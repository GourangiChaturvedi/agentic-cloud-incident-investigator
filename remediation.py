import json
from datetime import datetime, timezone
from pathlib import Path


AUDIT_FILE = Path(__file__).with_name("remediation_audit.jsonl")


def write_audit_event(event, details):
    """Append a timestamped remediation event to the local audit log."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": details,
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


def propose_remediation(diagnosis):
    """Generate a proposal without executing cloud actions."""
    if not isinstance(diagnosis, dict):
        raise ValueError("Diagnosis must be a dictionary.")

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
    
    write_audit_event(
    "proposal_created",
    {
        "action_id": action_id,
        "status": "proposed",
    },
)
   
    return {
        "status": "proposed",
        "action_id": action_id,
        "action": action,
        "requires_human_approval": True,
        "executed": False,
    }


def record_approval(proposal, approved):
    """Record a human decision without executing cloud actions."""
    if not isinstance(proposal, dict):
        raise ValueError("Proposal must be a dictionary.")

    if proposal.get("status") != "proposed":
        raise ValueError("Only proposed actions can be reviewed.")

    validate_remediation_action(proposal.get("action_id"))

    if not isinstance(approved, bool):
        raise ValueError("Approval must be True or False.")

    result = proposal.copy()
    result["approval_status"] = "approved" if approved else "rejected"
    result["executed"] = False

    write_audit_event(
    "approval_decision",
    {
        "action_id": result["action_id"],
        "approval_status": result["approval_status"],
        "executed": False,
    },
)

    return result
