
def propose_remediation(diagnosis):
    """Return a proposal only; never execute cloud actions."""
    if not isinstance(diagnosis, dict):
        raise ValueError("Diagnosis must be a dictionary.")

    cause = diagnosis.get("probable_root_cause", "")
    if not isinstance(cause, str) or not cause.strip():
        raise ValueError("A probable root cause is required.")

    if "cpu" in cause.lower() or "overload" in cause.lower():
        action = (
            "Review CPU utilization, request load, and application "
            "performance before deciding whether to scale."
        )
    else:
        action = (
            "Gather more diagnostic evidence before selecting a "
            "remediation action."
        )

    return {
        "status": "proposed",
        "action": action,
        "requires_human_approval": True,
        "executed": False,
    }


def test_proposal_does_not_execute_actions():
    diagnosis = {
        "probable_root_cause": "Application or workload CPU saturation"
    }

    proposal = propose_remediation(diagnosis)

    assert proposal["status"] == "proposed"
    assert proposal["requires_human_approval"] is True
    assert proposal["executed"] is False


def test_invalid_diagnosis_is_rejected():
    try:
        propose_remediation({})
    except ValueError:
        return

    raise AssertionError("An empty diagnosis should be rejected.")


if __name__ == "__main__":
    test_proposal_does_not_execute_actions()
    test_invalid_diagnosis_is_rejected()
    print("Remediation safety tests passed.")
