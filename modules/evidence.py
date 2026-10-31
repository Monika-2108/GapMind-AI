import re


STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on",
    "for", "with", "by", "from", "is", "are", "was", "were", "be",
    "been", "being", "that", "this", "these", "those", "it", "its",
    "as", "at", "about", "into", "their", "they", "them", "which",
    "who", "what", "when", "where", "how", "can", "could", "may",
    "might", "should", "would", "will", "has", "have", "had",
    "also", "more", "than", "such", "while", "under", "over"
}

NEGATION_WORDS = {
    "not", "no", "never", "neither", "cannot", "can't",
    "doesn't", "don't", "isn't", "aren't", "without"
}

OPPOSITE_PAIRS = [
    ("increase", "decrease"),
    ("increases", "decreases"),
    ("improve", "reduce"),
    ("improves", "reduces"),
    ("improved", "reduced"),
    ("improve", "worsen"),
    ("improves", "worsens"),
    ("higher", "lower"),
    ("greater", "lesser"),
    ("effective", "ineffective"),
    ("safe", "unsafe"),
    ("beneficial", "harmful"),
    ("support", "oppose"),
    ("supports", "opposes"),
    ("available", "unavailable"),
    ("affordable", "unaffordable"),
    ("accessible", "inaccessible"),
    ("present", "absent"),
    ("allow", "prohibit"),
    ("allows", "prohibits"),
]


def _tokens(text):
    words = re.findall(r"[a-zA-Z]+", str(text).lower())
    return {
        word for word in words
        if word not in STOP_WORDS and len(word) > 2
    }


def _has_negation(text):
    words = set(re.findall(r"[a-zA-Z']+", str(text).lower()))
    return bool(words.intersection(NEGATION_WORDS))


def _has_opposite_terms(first, second):
    first_words = _tokens(first)
    second_words = _tokens(second)

    for positive, negative in OPPOSITE_PAIRS:
        if (
            positive in first_words and negative in second_words
        ) or (
            negative in first_words and positive in second_words
        ):
            return True

    return False


def _extract_context(text):
    text = str(text).lower()

    return {
        "years": set(re.findall(r"\b(?:19|20)\d{2}\b", text)),
        "percentages": set(
            re.findall(r"\b\d+(?:\.\d+)?\s*%", text)
        ),
        "units": set(re.findall(
            r"\b(?:percent|percentage|million|billion|thousand|"
            r"rupees|inr|usd|kg|km|hours|days|months|years)\b",
            text
        )),
        "populations": set(re.findall(
            r"\b(?:men|women|male|female|children|adults|"
            r"youth|rural|urban|workers|students|households|"
            r"people|population|aged \d+)\b",
            text
        )),
        "locations": set(re.findall(
            r"\b(?:india|karnataka|bengaluru|bangalore|"
            r"delhi|mumbai|rural india|urban india)\b",
            text
        )),
    }


def _claims_are_comparable(first, second):
    first_tokens = _tokens(first)
    second_tokens = _tokens(second)

    if len(first_tokens) < 3 or len(second_tokens) < 3:
        return False

    shared = first_tokens.intersection(second_tokens)

    if len(shared) < 2:
        return False

    similarity = len(shared) / min(
        len(first_tokens),
        len(second_tokens)
    )

    if similarity < 0.30:
        return False

    first_context = _extract_context(first)
    second_context = _extract_context(second)

    for key in ("years", "populations", "locations", "units"):
        a = first_context[key]
        b = second_context[key]

        if a and b and a.isdisjoint(b):
            return False

    same_percentage_context = (
        not first_context["percentages"]
        or not second_context["percentages"]
        or first_context["percentages"]
        == second_context["percentages"]
    )

    opposite = _has_opposite_terms(first, second)
    negation_difference = (
        _has_negation(first) != _has_negation(second)
    )

    return opposite or (
        negation_difference and same_percentage_context
    )


def build_evidence_map(analysis, sources):
    evidence_map = []

    source_lookup = {
        source.get("source_id", index): source
        for index, source in enumerate(sources, start=1)
    }

    for claim in analysis.get("claims", []):
        references = []

        for source_id in claim.get("source_ids", []):
            source = source_lookup.get(source_id)

            if source:
                references.append({
                    "source_id": source_id,
                    "title": source.get("title", "Untitled source"),
                    "url": source.get("url"),
                    "source_type": source.get("source_type"),
                })

        excerpt = claim.get("supporting_excerpt", "")

        evidence_map.append({
            "claim": claim.get("claim_text", ""),
            "claim_type": claim.get("claim_type", "statement"),
            "confidence": claim.get("confidence", "unassessed"),
            "supporting_excerpt": excerpt,
            "evidence_status": (
                "Supported" if excerpt and references
                else "Unverified"
            ),
            "references": references,
        })

    return evidence_map


def validate_contradictions(analysis, sources):
    valid_ids = {
        source.get("source_id", index)
        for index, source in enumerate(sources, start=1)
    }

    validated = []
    seen_pairs = set()

    for item in analysis.get("contradictions", []):
        first_ids = item.get("claim_a_source_ids", [])
        second_ids = item.get("claim_b_source_ids", [])

        first_claim = str(item.get("claim_a", "")).strip()
        second_claim = str(item.get("claim_b", "")).strip()

        if not first_claim or not second_claim:
            continue

        if not isinstance(first_ids, list) or not isinstance(second_ids, list):
            continue

        if not first_ids or not second_ids:
            continue

        if not set(first_ids + second_ids).issubset(valid_ids):
            continue

        if not _claims_are_comparable(first_claim, second_claim):
            continue

        pair_key = tuple(sorted([
            first_claim.lower(),
            second_claim.lower()
        ]))

        if pair_key in seen_pairs:
            continue

        seen_pairs.add(pair_key)

        validated.append({
            "description": item.get("description", ""),
            "claim_a": first_claim,
            "claim_a_source_ids": first_ids,
            "claim_b": second_claim,
            "claim_b_source_ids": second_ids,
            "severity": item.get("severity", "medium"),
            "status": (
                "Potential conflict — human verification required"
            ),
            "comparison_note": (
                "Automated text comparison only. Check the original "
                "dates, populations, locations, units and methodology."
            ),
        })

    return validated


def build_source_network(evidence_map):
    nodes = []
    edges = []
    seen_sources = set()

    for claim_index, item in enumerate(evidence_map, start=1):
        claim_node = f"claim_{claim_index}"

        nodes.append({
            "id": claim_node,
            "label": item["claim"][:65],
            "type": "claim",
        })

        for reference in item["references"]:
            source_id = reference["source_id"]
            source_node = f"source_{source_id}"

            if source_id not in seen_sources:
                nodes.append({
                    "id": source_node,
                    "label": reference["title"][:45],
                    "type": "source",
                })
                seen_sources.add(source_id)

            edges.append({
                "source": source_node,
                "target": claim_node,
            })

    return {
        "nodes": nodes,
        "edges": edges,
    }


def compare_claims_by_source(analysis):
    grouped = {}

    for claim in analysis.get("claims", []):
        for source_id in claim.get("source_ids", []):
            grouped.setdefault(source_id, []).append(
                claim.get("claim_text", "")
            )

    return grouped
