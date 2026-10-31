PRIORITY_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def score_gap(gap, source_count):
    priority = str(gap.get("priority", "medium")).lower()
    priority_weight = PRIORITY_WEIGHTS.get(priority, 2)

    related_ids = gap.get("related_source_ids", [])
    related_count = len(set(related_ids))

    # More important questions receive higher scores.
    # A gap connected to fewer sources may indicate weaker coverage.
    coverage_factor = max(0, source_count - related_count)

    score = (priority_weight * 20) + min(coverage_factor * 10, 20)

    return {
        "score": min(score, 100),
        "priority": priority,
        "priority_points": priority_weight * 20,
        "coverage_points": min(coverage_factor * 10, 20),
        "explanation": (
            f"Priority: {priority}. "
            f"Related sources: {related_count} of {source_count}. "
            "This is a heuristic ranking, not a probability or accuracy score."
        ),
    }


def score_all_gaps(gaps, source_count):
    scored_gaps = []

    for gap in gaps:
        scoring = score_gap(gap, source_count)

        scored_gaps.append({
            **gap,
            **scoring,
        })

    return sorted(
        scored_gaps,
        key=lambda item: item["score"],
        reverse=True
    )


def get_priority_counts(gaps):
    counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for gap in gaps:
        priority = str(gap.get("priority", "medium")).lower()

        if priority in counts:
            counts[priority] += 1

    return counts