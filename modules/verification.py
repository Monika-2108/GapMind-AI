def build_verification_checklist(analysis, scored_gaps):
    checklist = []

    for gap in scored_gaps:
        checklist.append({
            "question": gap.get("question", ""),
            "reason": gap.get("reason", ""),
            "priority": gap.get("priority", "medium"),
            "impact_score": gap.get("score", 0),
            "status": "Pending verification",
            "source_ids": gap.get("related_source_ids", []),
        })

    for question in analysis.get("verification_questions", []):
        checklist.append({
            "question": question.get("question", ""),
            "reason": question.get("reason", ""),
            "priority": question.get("priority", "medium"),
            "impact_score": None,
            "status": "Pending verification",
            "source_ids": [],
        })

    priority_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    checklist.sort(
        key=lambda item: priority_order.get(
            str(item["priority"]).lower(), 1
        )
    )

    return checklist


def update_checklist_status(checklist, index, status):
    allowed_statuses = [
        "Pending verification",
        "In progress",
        "Verified",
        "Unable to verify",
    ]

    if status not in allowed_statuses:
        raise ValueError("Invalid verification status.")

    if 0 <= index < len(checklist):
        checklist[index]["status"] = status

    return checklist


def checklist_summary(checklist):
    total = len(checklist)

    verified = sum(
        item["status"] == "Verified"
        for item in checklist
    )

    pending = sum(
        item["status"] == "Pending verification"
        for item in checklist
    )

    return {
        "total": total,
        "verified": verified,
        "pending": pending,
        "completion_percent": round(
            (verified / total) * 100
        ) if total else 0,
    }