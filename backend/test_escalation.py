from escalation_engine import decide_escalation


current_report = {
    "report_id": 9,
    "predicted_class": "Potassium Deficiency",
    "risk_score": 71.5,
    "confidence": 0.42,
    "risk_level": "CRITICAL",
}

comparison = {
    "condition_changed": True,
    "risk_increased": True,
}


result = decide_escalation(
    current_report=current_report,
    comparison=comparison,
)

print(result)