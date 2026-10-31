import json
from core.gemini import generate_json


MAX_CONTENT_PER_SOURCE = 2500


def analyze_sources(topic, sources):
    if not sources:
        raise ValueError("Add at least one source before analysis.")

    source_material = []

    for index, source in enumerate(sources, start=1):
        content = source.get("content", "")

        if not isinstance(content, str) or not content.strip():
            continue

        source_material.append({
            "source_id": index,
            "title": source.get("title", "Untitled"),
            "url": source.get("url"),
            "published_date": source.get("published_date"),
            "content": content[:MAX_CONTENT_PER_SOURCE]
        })

    if not source_material:
        raise ValueError("No readable source content was found.")

    valid_ids = {
        source["source_id"] for source in source_material
    }

    prompt = f"""
You are GapMind AI, an evidence intelligence analyst.

TOPIC: {topic}

SOURCES:
{json.dumps(source_material, ensure_ascii=False)}

Analyze ONLY the supplied source content.

Return valid JSON with exactly these seven keys:

{{
  "summary": [
    {{"point": "Short finding", "source_ids": [1]}}
  ],
  "claims": [
    {{
      "claim_text": "Specific source-supported claim",
      "source_ids": [1],
      "supporting_excerpt": "Exact sentence copied from the source",
      "claim_type": "finding",
      "confidence": "high"
    }}
  ],
  "gaps": [
    {{
      "question": "What remains unanswered?",
      "reason": "Why it matters",
      "missing_information": "Specific missing detail",
      "priority": "high",
      "related_source_ids": [1]
    }}
  ],
  "contradictions": [
    {{
      "description": "Explain the possible conflict",
      "claim_a": "First claim",
      "claim_a_source_ids": [1],
      "claim_b": "Second claim",
      "claim_b_source_ids": [2],
      "severity": "medium"
    }}
  ],
  "freshness_warnings": [
    {{"source_id": 1, "reason": "Date is unknown"}}
  ],
  "verification_questions": [
    {{
      "question": "What should be checked?",
      "reason": "Why it needs checking",
      "priority": "medium"
    }}
  ],
  "limitations": ["Analysis limitation"]
}}

RULES:
- Maximum 3 summary points.
- Maximum 5 claims.
- Maximum 3 gaps.
- Maximum 2 contradictions.
- Maximum 3 verification questions.
- Every claim must have valid source IDs.
- Every supporting excerpt must be copied exactly from a cited source.
- Never invent or rewrite an excerpt.
- If no exact supporting excerpt exists, use an empty string.
- Never invent facts, statistics or dates.
- Report only possible source-supported contradictions.
- Do not treat different numbers alone as proof of contradiction.
- Consider dates, populations, locations, units and methodologies.
- A gap means the supplied sources do not answer something.
- Mark unknown dates clearly.
- If only one source is supplied, mention the comparison limitation.
- Keep every answer short and specific.
- Return JSON only.
"""

    result = generate_json(prompt)

    if not isinstance(result, dict):
        raise ValueError("AI returned an invalid analysis.")

    required_keys = [
        "summary",
        "claims",
        "gaps",
        "contradictions",
        "freshness_warnings",
        "verification_questions",
        "limitations"
    ]

    for key in required_keys:
        if not isinstance(result.get(key), list):
            raise ValueError(f"Invalid analysis section: {key}")

    for claim in result["claims"]:
        ids = claim.get("source_ids", [])

        if not isinstance(ids, list) or not ids:
            raise ValueError("A claim has no source references.")

        if not set(ids).issubset(valid_ids):
            raise ValueError("A claim contains invalid source references.")

        excerpt = claim.get("supporting_excerpt", "")

        if not isinstance(excerpt, str):
            claim["supporting_excerpt"] = ""

        elif excerpt:
            cited_sources = [
                source for source in source_material
                if source["source_id"] in ids
            ]

            if not any(
                excerpt in source["content"]
                for source in cited_sources
            ):
                claim["supporting_excerpt"] = ""

    for item in result["summary"]:
        ids = item.get("source_ids", [])

        if not isinstance(ids, list) or not set(ids).issubset(valid_ids):
            raise ValueError(
                "A summary point contains invalid source references."
            )

    if len(source_material) < 2:
        result["limitations"].append(
            "Only one readable source was analysed. "
            "Cross-source comparison is limited."
        )

    return result