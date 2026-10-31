def calculate_evidence_coverage(claims, sources):
    total_claims = len(claims)
    total_sources = len(sources)

    single_source = 0
    multi_source = 0
    unsupported = 0
    source_usage = {}

    for claim in claims:
        source_ids = set(claim.get("source_ids", []))

        if not source_ids:
            unsupported += 1
        elif len(source_ids) == 1:
            single_source += 1
        else:
            multi_source += 1

        for source_id in source_ids:
            source_usage[source_id] = source_usage.get(source_id, 0) + 1

    supported_claims = total_claims - unsupported

    return {
        "total_claims": total_claims,
        "total_sources": total_sources,
        "single_source_claims": single_source,
        "multi_source_claims": multi_source,
        "unsupported_claims": unsupported,
        "multi_source_percentage": round(
            multi_source / total_claims * 100, 1
        ) if total_claims else 0,
        "supported_claim_percentage": round(
            supported_claims / total_claims * 100, 1
        ) if total_claims else 0,
        "source_usage": source_usage,
        "warning": (
            "Source links do not independently prove a claim. "
            "Check source independence and original evidence."
        )
    }
