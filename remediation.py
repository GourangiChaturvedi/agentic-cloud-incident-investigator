import json
from datetime import datetime, timezone
from pathlib import Path


AUDIT_FILE = Path(__file__).with_name("remediation_audit.jsonl")


def write_audit_event(event, details):
    """Append a timestamped remediation event to the local audit log."""
    if not isinstance(details, dict):
        raise ValueError("Audit event details must be a dictionary.")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": details.copy(),
    }

    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


ALLOWED_ACTIONS = {
    "review_cpu_and_consider_scaling",
    "gather_more_diagnostic_evidence",
}


def validate_remediation_action(action_id):
    """Reject actions that are not explicitly allowlisted."""
    if action_id not in ALLOWED_ACTIONS:
        raise ValueError(
            f"Remediation action is not allowed: {action_id}"
        )
    return True


def propose_remediation(diagnosis, investigation_id=None):
    """Generate and audit a proposal without executing cloud actions."""
    if not isinstance(diagnosis, dict):
        raise ValueError("Diagnosis must be a dictionary.")

    # Accept an ID supplied directly or included in the diagnosis.
    if investigation_id is None:
        investigation_id = diagnosis.get("investigation_id")

    if investigation_id is not None:
        if not isinstance(investigation_id, str) or not investigation_id.strip():
            raise ValueError("Investigation ID must be a non-empty string.")

    cause = diagnosis.get("probable_root_cause", "")
    if not isinstance(cause, str) or not cause.strip():
        raise ValueError("A probable root cause is required.")

    if "cpu" in cause.lower() or "overload" in cause.lower():
        action_id = "review_cpu_and_consider_scaling"
        action = (
            "Review CPU utilization, request load, and application "
            "performance before deciding whether to scale."
        )
    else:
        action_id = "gather_more_diagnostic_evidence"
        action = (
            "Gather more diagnostic evidence before selecting a "
            "remediation action."
        )

    validate_remediation_action(action_id)

    proposal = {
        "status": "proposed",
        "action_id": action_id,
        "action": action,
        "requires_human_approval": True,
        "executed": False,
    }

    if investigation_id is not None:
        proposal["investigation_id"] = investigation_id

    audit_details = {
        "action_id": action_id,
        "status": "proposed",
    }

    if investigation_id is not None:
        audit_details["investigation_id"] = investigation_id

    write_audit_event("proposal_created", audit_details)

    return proposal


def record_approval(proposal, approved, investigation_id=None):
    """Record a human decision without executing cloud actions."""
    if not isinstance(proposal, dict):
        raise ValueError("Proposal must be a dictionary.")

    if proposal.get("status") != "proposed":
        raise ValueError("Only proposed actions can be reviewed.")

    validate_remediation_action(proposal.get("action_id"))

    if not isinstance(approved, bool):
        raise ValueError("Approval must be True or False.")

    # Preserve the proposal's ID unless the caller supplies one explicitly.
    if investigation_id is None:
        investigation_id = proposal.get("investigation_id")

    if investigation_id is not None:
        if not isinstance(investigation_id, str) or not investigation_id.strip():
            raise ValueError("Investigation ID must be a non-empty string.")

    decision = "approved" if approved else "rejected"

    result = proposal.copy()
    result["status"] = decision
    result["approval_status"] = decision
    result["executed"] = False

    if investigation_id is not None:
        result["investigation_id"] = investigation_id

    audit_details = {
        "action_id": result["action_id"],
        "approval_status": decision,
        "executed": False,
    }

    if investigation_id is not None:
        audit_details["investigation_id"] = investigation_id

    write_audit_event("approval_decision", audit_details)

    return result
