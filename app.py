
import json
import uuid
from pathlib import Path

import streamlit as st

from diagnostic_tools import (
    collect_diagnostic_evidence,
    record_investigation,
)
from llm_tool_test import investigate_incident
from remediation import (
    propose_remediation,
    record_approval,
)


st.set_page_config(
    page_title="Cloud Incident Investigator",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Agentic AI Cloud Incident Investigator")
st.caption(
    "Investigate simulated cloud incidents and inspect real AWS telemetry "
    "without mixing evidence sources."
)


# --------------------------------------------------
# Simulated incidents
# --------------------------------------------------

incidents = {
    "Application Overload": {
        "incident_id": "INC-001",
        "incident_type": "high_cpu",
        "cpu_usage_percent": 96,
        "database_connections": 35,
        "logs": [
            "CPU utilization exceeded 90%",
            "Repeated request timeouts detected",
            "Application response time increased",
        ],
        "recent_deployment": True,
    },
    "Database Connection Pressure": {
        "incident_id": "INC-002",
        "incident_type": "database_pressure",
        "cpu_usage_percent": 45,
        "database_connections": 95,
        "logs": [
            "Database connection limit nearly reached",
            "Database response time increased",
        ],
        "recent_deployment": False,
    },
    "Normal Operation": {
        "incident_id": "INC-003",
        "incident_type": "normal",
        "cpu_usage_percent": 25,
        "database_connections": 20,
        "logs": [
            "Application health check successful",
            "Application operating normally",
        ],
        "recent_deployment": False,
    },
    "Unclear Dependency Issue": {
        "incident_id": "INC-004",
        "incident_type": "unknown",
        "cpu_usage_percent": 45,
        "database_connections": 30,
        "logs": [
            "External dependency response time increased",
        ],
        "recent_deployment": False,
    },
}


# --------------------------------------------------
# Session state
# --------------------------------------------------

STATE_DEFAULTS = {
    "investigation_display": None,
    "remediation_proposal": None,
    "remediation_decision": None,
    "active_investigation_id": None,
    "proposal_investigation_id": None,
}

for key, default_value in STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# --------------------------------------------------
# Incident overview
# --------------------------------------------------

st.subheader("Incident Overview")

selected_name = st.selectbox(
    "Select a simulated incident",
    list(incidents.keys()),
)

incident = incidents[selected_name]

st.markdown(
    f"**Incident ID:** `{incident['incident_id']}`  "
    "| **Environment:** Simulated"
)

col1, col2, col3 = st.columns(3)

with col1:
    cpu = incident["cpu_usage_percent"]
    st.metric("CPU Utilization", f"{cpu}%")
    st.caption("High" if cpu > 90 else "Within threshold")

with col2:
    db = incident["database_connections"]
    st.metric("Database Connections", db)
    st.caption("High" if db > 80 else "Within threshold")

with col3:
    logs = incident["logs"]
    st.metric("Log Entries", len(logs))
    timeout_count = sum("timeout" in log.lower() for log in logs)
    st.caption(f"{timeout_count} timeout-related entries")

with st.expander("View original incident logs"):
    for log in incident["logs"]:
        st.write(f"• {log}")


st.divider()
st.subheader("Incident Investigation")


# --------------------------------------------------
# Run a new investigation
# --------------------------------------------------

if st.button("🔍 Investigate Incident", type="primary"):
    progress = st.progress(0, text="Validating incident...")
    activity = st.status(
        "Investigation in progress",
        expanded=True,
    )

    try:
        progress.progress(10, text="Validating incident...")
        activity.write("Validating incident inputs...")

        progress.progress(20, text="Collecting AWS evidence...")
        activity.write("Requesting CPU metrics from CloudWatch...")
        activity.write("Checking configured CloudWatch log group...")

        collection_result = collect_diagnostic_evidence(
            incident,
            source="aws",
        )

        if collection_result.get("status") == "error":
            raise RuntimeError(
                collection_result.get(
                    "message",
                    "Evidence collection failed.",
                )
            )

        collection_data = collection_result.get("data", {})
        source_label = collection_data.get("source", "unknown")

        progress.progress(45, text="Investigating with Bedrock...")
        activity.write("Running the Bedrock agent...")

        try:
            agent_result = investigate_incident(incident)
        except Exception as agent_error:
            agent_result = {
                "status": "error",
                "source": "none",
                "diagnosis": None,
                "evidence": [],
                "message": (
                    "The Bedrock agent invocation failed. "
                    "The source-aware diagnosis will be retained. "
                    f"Details: {agent_error}"
                ),
            }

        progress.progress(75, text="Recording investigation results...")

        investigation = record_investigation(
            incident,
            collection_result,
        )

        if investigation.get("status") == "error":
            raise RuntimeError(
                investigation.get(
                    "message",
                    "Investigation could not be completed.",
                )
            )

        investigation_id = str(uuid.uuid4())

        st.session_state["investigation_display"] = {
            "investigation_id": investigation_id,
            "incident_id": incident["incident_id"],
            "source_label": source_label,
            "collection_result": collection_result,
            "investigation": investigation,
            "agent_result": agent_result,
        }

        st.session_state["active_investigation_id"] = investigation_id
        st.session_state["remediation_proposal"] = None
        st.session_state["remediation_decision"] = None
        st.session_state["proposal_investigation_id"] = None

        progress.progress(100, text="Investigation finished")
        activity.update(
            label="Investigation completed",
            state="complete",
            expanded=False,
        )

    except Exception as exc:
        progress.empty()
        activity.update(
            label="Investigation failed",
            state="error",
            expanded=True,
        )
        st.error(f"Investigation could not be completed: {exc}")


# --------------------------------------------------
# Display latest investigation
# --------------------------------------------------

display = st.session_state.get("investigation_display")

if display is not None:
    collection_result = display["collection_result"]
    collection_data = collection_result.get("data", {})
    investigation = display["investigation"]
    agent_result = display.get("agent_result", {})

    if display["incident_id"] != incident["incident_id"]:
        st.info(
            "The displayed results belong to a previously selected incident. "
            "Run a new investigation for the currently selected incident."
        )
        st.stop()

    investigation_id = display["investigation_id"]
    evidence = investigation.get("evidence", [])
    errors = investigation.get("errors", [])
    source_label = display["source_label"]
    fallback_used = collection_data.get("fallback_used", False)

    st.caption(
        f"Investigation ID: {investigation_id} "
        f"| Evidence source: {source_label} "
        f"| Simulated fallback used: {fallback_used}"
    )

    if source_label == "aws":
        st.info(
            "Real AWS telemetry is shown only where available. "
            "Simulated incident values are not treated as live measurements."
        )
    elif source_label == "simulated_fallback":
        st.warning(
            "AWS telemetry was unavailable. The fallback evidence is simulated."
        )

    # --------------------------------------------------
    # Bedrock agent result
    # --------------------------------------------------

    st.divider()
    st.subheader("Bedrock Agent Investigation")

    agent_status = agent_result.get("status", "error")
    agent_source = agent_result.get("source", "none")
    agent_diagnosis = agent_result.get("diagnosis")

    if agent_status == "success" and isinstance(agent_diagnosis, dict):
        st.success("The Bedrock agent returned a valid diagnosis.")

        st.write(
            "**Agent's probable root cause:** "
            f"{agent_diagnosis.get('probable_root_cause', 'Unavailable')}"
        )
        st.write(
            f"**Agent confidence:** {agent_diagnosis.get('confidence', 'Unknown')}"
        )
        st.write(
            f"**Agent uncertainty:** {agent_diagnosis.get('uncertainty', 'Not provided')}"
        )

        st.caption(
            f"Agent source: {agent_source} "
            f"| Model: {agent_result.get('model_id', 'configured Bedrock model')} "
            f"| Region: {agent_result.get('region', 'configured region')}"
        )

        if agent_result.get("message"):
            st.write(agent_result["message"])

        with st.expander("View agent supporting evidence"):
            st.json(agent_diagnosis.get("supporting_evidence", {}))

        with st.expander("View diagnostic tool calls made by the agent"):
            st.json(agent_result.get("evidence", []))

        elapsed = agent_result.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)):
            st.caption(f"Agent elapsed time: {elapsed:.3f} seconds")

    elif agent_status == "fallback":
        st.warning(
            "The Bedrock agent returned a simulated rule-based fallback. "
            "This is not a successful AI-agent diagnosis."
        )
        st.write(agent_result.get("message", ""))

        with st.expander("View fallback diagnosis and evidence"):
            st.json(agent_diagnosis or {})
            st.json(agent_result.get("evidence", []))

    else:
        st.warning("A valid Bedrock agent diagnosis is unavailable.")
        st.write(
            agent_result.get(
                "message",
                "No additional agent error details were returned.",
            )
        )

    # --------------------------------------------------
    # Locate evidence by tool name
    # --------------------------------------------------

    cpu_result = next(
        (
            item for item in evidence
            if item.get("tool") in (
                "get_cpu_metrics",
                "get_aws_cpu_metrics",
            )
        ),
        None,
    )

    db_result = next(
        (
            item for item in evidence
            if item.get("tool") == "get_database_metrics"
        ),
        None,
    )

    deployment_result = next(
        (
            item for item in evidence
            if item.get("tool") == "get_recent_deployments"
        ),
        None,
    )

    simulated_log_result = next(
        (
            item for item in evidence
            if item.get("tool") == "analyze_logs"
        ),
        None,
    )

    aws_log_result = next(
        (
            item for item in evidence
            if item.get("tool") == "get_aws_log_evidence"
        ),
        None,
    )

    cpu_data = cpu_result.get("data", {}) if cpu_result else {}
    db_data = db_result.get("data", {}) if db_result else {}
    deployment_data = (
        deployment_result.get("data", {}) if deployment_result else {}
    )
    simulated_log_data = (
        simulated_log_result.get("data", {}) if simulated_log_result else {}
    )
    aws_log_data = aws_log_result.get("data", {}) if aws_log_result else {}

    # --------------------------------------------------
    # Source-aware evidence interpretation
    # --------------------------------------------------

    is_live_aws = (
        source_label == "aws"
        and cpu_data.get("source") == "aws_cloudwatch"
    )

    aws_metrics = cpu_data.get("metrics", []) if is_live_aws else []

    aws_max_cpu = max(
        (
            metric.get("maximum_cpu", 0)
            for metric in aws_metrics
            if isinstance(metric.get("maximum_cpu"), (int, float))
        ),
        default=None,
    )

    valid_average_values = [
        metric["average_cpu"]
        for metric in aws_metrics
        if isinstance(metric.get("average_cpu"), (int, float))
    ]

    aws_average_cpu = (
        sum(valid_average_values) / len(valid_average_values)
        if valid_average_values
        else None
    )

    if is_live_aws:
        cpu_high = aws_max_cpu is not None and aws_max_cpu >= 80
    else:
        cpu_high = cpu_data.get("assessment") == "high"

    db_high = db_data.get("assessment") == "high"
    deployment_detected = deployment_data.get("recent_deployment") is True

    findings = simulated_log_data.get("findings", [])
    aws_events = aws_log_data.get("events", [])

    simulated_log_issue = any(
        not (
            isinstance(finding, str)
            and "no matching" in finding.lower()
        )
        for finding in findings
    )

    log_issue = (
        bool(aws_events)
        if source_label == "aws"
        else simulated_log_issue
    )

    # --------------------------------------------------
    # Investigation summary
    # --------------------------------------------------

    st.divider()
    st.subheader("Investigation Results")

    summary1, summary2, summary3 = st.columns(3)

    with summary1:
        st.metric(
            "Successful Tools",
            investigation.get("successful_tool_count", 0),
        )

    with summary2:
        st.metric(
            "Tool Errors",
            investigation.get("error_count", len(errors)),
        )

    with summary3:
        st.metric("Evidence Sources", len(evidence))

    if errors:
        st.warning(
            "Some diagnostic tools failed. Interpret the results cautiously."
        )

    if collection_data.get("unavailable"):
        st.warning(
            "Some configured AWS evidence sources are unavailable. "
            "See the raw collection result below."
        )

    # --------------------------------------------------
    # Source-aware diagnosis
    # --------------------------------------------------

    if source_label == "aws":
        if is_live_aws and aws_metrics:
            if errors:
                cause = "Inconclusive"
                confidence = "Low"
                uncertainty = (
                    "Some diagnostic tools failed. Additional evidence "
                    "is needed to establish a cause."
                )
            elif cpu_high:
                cause = "Application or workload CPU saturation"
                confidence = "Medium"
                uncertainty = (
                    "Live CPU metrics indicate elevated utilization, "
                    "but the underlying cause is not established."
                )
            else:
                cause = "No confirmed resource-pressure cause"
                confidence = "Low"
                uncertainty = (
                    "Available live CPU metrics do not establish resource "
                    "pressure. Live database metrics are not collected, "
                    "so a database-related incident cannot be ruled out."
                )
        else:
            cause = "Inconclusive"
            confidence = "Low"
            uncertainty = (
                "Usable live AWS CPU metrics were not available. "
                "A live AWS root cause cannot be established."
            )

    elif errors:
        cause = "Inconclusive"
        confidence = "Low"
        uncertainty = (
            "One or more diagnostic tools failed. Additional evidence is needed."
        )

    elif not cpu_result or not db_result:
        cause = "Inconclusive"
        confidence = "Low"
        uncertainty = "Required simulated CPU or database evidence is missing."

    elif cpu_high and db_high:
        cause = "Combined CPU and database connection pressure"
        confidence = "Medium"
        uncertainty = (
            "Both simulated resource signals exceed their thresholds. "
            "The initiating cause remains unconfirmed."
        )

    elif cpu_high:
        cause = "Application or workload CPU saturation"
        confidence = "Medium"
        uncertainty = (
            "High simulated CPU utilization is confirmed, but its cause "
            "has not been proven."
        )

    elif db_high:
        cause = "Database connection pressure"
        confidence = "Medium"
        uncertainty = (
            "Simulated connection usage exceeds its threshold, but the "
            "reason for the increase is unconfirmed."
        )

    elif not log_issue:
        cause = "No confirmed resource-pressure cause"
        confidence = "Medium"
        uncertainty = (
            "Available simulated checks did not identify a major resource "
            "pressure signal. They cannot rule out every incident."
        )

    else:
        cause = "Inconclusive"
        confidence = "Low"
        uncertainty = (
            "The available evidence does not establish a probable root cause."
        )

    if (
        source_label != "aws"
        and agent_status == "success"
        and isinstance(agent_diagnosis, dict)
    ):
        cause = agent_diagnosis.get("probable_root_cause", cause)
        confidence = str(
            agent_diagnosis.get("confidence", confidence)
        ).title()
        uncertainty = agent_diagnosis.get("uncertainty", uncertainty)

    elif source_label == "aws" and agent_status == "success":
        st.info(
            "The Bedrock agent result is shown separately because its input "
            "includes the simulated incident payload. The diagnosis below "
            "is based on the source-aware AWS evidence and does not treat "
            "simulated CPU, database, or deployment values as live telemetry."
        )

    # --------------------------------------------------
    # Proposal lifecycle: one proposal per investigation ID
    # --------------------------------------------------

    proposal = st.session_state.get("remediation_proposal")
    proposal_investigation_id = st.session_state.get(
        "proposal_investigation_id"
    )

    if proposal is None or proposal_investigation_id != investigation_id:
        try:
            # Pass the ID into remediation.py so new audit records are linked.
            proposal = propose_remediation(
                {
                    "probable_root_cause": cause,
                    "investigation_id": investigation_id,
                },
                investigation_id=investigation_id,
            )

            st.session_state["remediation_proposal"] = proposal
            st.session_state["proposal_investigation_id"] = investigation_id
            st.session_state["remediation_decision"] = None

        except Exception as exc:
            st.session_state["remediation_proposal"] = None
            st.session_state["proposal_investigation_id"] = None
            st.error(f"Could not create remediation proposal: {exc}")

    # --------------------------------------------------
    # Diagnosis summary
    # --------------------------------------------------

    st.markdown("### Diagnosis Summary")
    st.write(f"**Probable Cause:** {cause}")

    confidence_col, uncertainty_col = st.columns(2)

    with confidence_col:
        st.metric("Confidence Level", confidence)

    with uncertainty_col:
        st.markdown("**Diagnostic Uncertainty**")
        st.write(uncertainty)

    # --------------------------------------------------
    # Evidence panels
    # --------------------------------------------------

    st.divider()
    st.subheader("Diagnostic Evidence")

    metric_tab, log_tab, deployment_tab, raw_tab = st.tabs(
        ["Metrics", "Log Findings", "Deployment", "All Tool Results"]
    )

    with metric_tab:
        metric_col1, metric_col2 = st.columns(2)

        with metric_col1:
            st.markdown("**CPU Metrics**")

            if is_live_aws:
                if aws_metrics:
                    st.write(f"Region: {cpu_data.get('region')}")
                    st.write(f"Datapoints: {len(aws_metrics)}")

                    if aws_average_cpu is not None:
                        st.metric(
                            "Mean of datapoint averages",
                            f"{aws_average_cpu:.3f}%",
                        )

                    if aws_max_cpu is not None:
                        st.metric(
                            "Highest datapoint maximum",
                            f"{aws_max_cpu:.3f}%",
                        )

                    st.caption(
                        "These are real CloudWatch readings, not the "
                        "selected simulated incident's CPU percentage."
                    )
                    st.json(aws_metrics)
                else:
                    st.warning("Live AWS CPU metrics are unavailable.")
            elif cpu_result:
                st.json(cpu_data)
            else:
                st.warning("CPU evidence unavailable.")

        with metric_col2:
            st.markdown("**Database Metrics**")

            if db_result:
                st.json(db_data)
            elif source_label == "aws":
                st.warning(
                    "Live AWS database connection evidence is not "
                    "currently collected by this workflow."
                )
            else:
                st.warning("Database evidence unavailable.")

    with log_tab:
        if source_label == "aws":
            if aws_events:
                st.write(f"CloudWatch log events: {len(aws_events)}")
                for event in aws_events:
                    st.write(event.get("message", ""))
            elif aws_log_result:
                st.warning(
                    aws_log_result.get(
                        "message",
                        "No CloudWatch log events were returned.",
                    )
                )
            else:
                st.warning("AWS log evidence is unavailable.")
        elif simulated_log_result:
            for finding in findings:
                st.write(f"• {finding}")
        else:
            st.warning("Simulated log analysis evidence is unavailable.")

    with deployment_tab:
        if source_label == "aws":
            st.info(
                "Live deployment evidence is not currently collected "
                "by this AWS evidence workflow."
            )
        elif deployment_result:
            st.write(
                "Recent deployment detected."
                if deployment_detected
                else "No recent deployment detected."
            )
        else:
            st.warning("Deployment evidence unavailable.")

    with raw_tab:
        st.markdown("**Collection result**")
        st.json(collection_result)

        st.markdown("**Processed investigation**")
        st.json(investigation)

        st.markdown("**Bedrock agent result**")
        st.json(agent_result)

    # --------------------------------------------------
    # Supporting evidence
    # --------------------------------------------------

    st.markdown("### Supporting Evidence")

    support = []

    if is_live_aws and aws_metrics:
        support.append(
            f"Retrieved {len(aws_metrics)} live CloudWatch CPU datapoints."
        )
        if aws_max_cpu is not None:
            support.append(
                f"The highest maximum CPU reading was {aws_max_cpu:.3f}%."
            )
    elif cpu_result:
        support.append(
            f"Simulated CPU assessment: {cpu_data.get('assessment', 'unknown')}."
        )

    if db_result:
        support.append(
            "Database connections: "
            f"{db_data.get('database_connections', 'unknown')}."
        )

    if source_label == "aws" and aws_events:
        support.append(
            f"Retrieved {len(aws_events)} live CloudWatch log events."
        )
    elif source_label != "aws" and simulated_log_result:
        support.extend(
            finding for finding in findings
            if isinstance(finding, str)
            and "no matching" not in finding.lower()
        )

    if deployment_result:
        support.append(
            "A recent simulated deployment was detected."
            if deployment_detected
            else "No recent simulated deployment was detected."
        )

    if support:
        for item in support:
            st.write(f"• {item}")
    else:
        st.info("No supporting evidence is available.")

    # --------------------------------------------------
    # Alternative explanations
    # --------------------------------------------------

    st.markdown("### Alternative Explanations")

    alternatives = []

    if source_label == "aws":
        if cpu_high:
            alternatives.append(
                "High live CPU may relate to increased workload or "
                "inefficient processing; further evidence is needed."
            )

        if not db_result:
            alternatives.append(
                "Database pressure cannot be assessed because live database "
                "connection metrics are not collected here."
            )

        if not aws_events:
            alternatives.append(
                "Application log evidence is missing or unavailable."
            )

        if not alternatives:
            alternatives.append(
                "Available live telemetry may not capture the underlying "
                "incident or its initiating cause."
            )
    else:
        if cpu_high:
            alternatives.append(
                "Increased request volume or an inefficient application workload."
            )

        if db_high:
            alternatives.append(
                "Slow queries, connection leaks, or insufficient connection-pool capacity."
            )

        if deployment_detected:
            alternatives.append(
                "The recent simulated deployment may be related, but timing "
                "alone does not establish causation."
            )

        if not alternatives:
            alternatives.append(
                "The incident may involve an unmonitored dependency, "
                "intermittent failure, or an issue not represented by "
                "the simulated signals."
            )

    for alternative in alternatives:
        st.write(f"• {alternative}")

    if errors:
        st.markdown("### Tool Errors")
        st.json(errors)

    unavailable = collection_data.get("unavailable", [])
    if unavailable:
        st.markdown("### Unavailable Evidence Sources")
        st.json(unavailable)


# --------------------------------------------------
# Remediation recommendation and human approval
# --------------------------------------------------

st.divider()
st.subheader("Remediation Recommendation")

proposal = st.session_state.get("remediation_proposal")
display = st.session_state.get("investigation_display")

if (
    display is None
    or proposal is None
    or st.session_state.get("proposal_investigation_id")
    != display.get("investigation_id")
):
    st.info("Run an investigation to generate its remediation proposal.")

else:
    st.markdown("**Proposed action**")
    st.write(proposal["action"])

    st.markdown("**Rationale**")
    st.write(
        "This recommendation is based on the investigation diagnosis. "
        "Review the evidence and uncertainty before deciding."
    )

    st.caption(
        "Recommendation only: no cloud action executes automatically."
    )

    st.write(f"**Investigation ID:** `{display['investigation_id']}`")
    st.write(f"**Action ID:** `{proposal['action_id']}`")

    decision = st.session_state.get("remediation_decision")
    display_status = (
        decision.get(
            "approval_status",
            decision.get("status", "recorded"),
        )
        if decision is not None
        else proposal.get("status", "proposed")
    )

    st.write(f"**Proposal status:** {display_status}")
    st.write("**Executed:** No")

    if decision is None:
        approve_col, reject_col = st.columns(2)

        with approve_col:
            if st.button(
                "Approve Recommendation",
                key="approve_remediation",
            ):
                try:
                    st.session_state["remediation_decision"] = (
                        record_approval(
                            proposal,
                            True,
                            investigation_id=display["investigation_id"],
                        )
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Approval could not be recorded: {exc}")

        with reject_col:
            if st.button(
                "Reject Recommendation",
                key="reject_remediation",
            ):
                try:
                    st.session_state["remediation_decision"] = (
                        record_approval(
                            proposal,
                            False,
                            investigation_id=display["investigation_id"],
                        )
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Rejection could not be recorded: {exc}")

    else:
        approval_status = decision.get(
            "approval_status",
            decision.get("status", "recorded"),
        )
        st.write(f"**Human decision:** {str(approval_status).title()}")
        st.write("**Executed:** No")


# --------------------------------------------------
# Remediation audit trail
# --------------------------------------------------

st.divider()
st.subheader("Remediation Audit Trail")

audit_file = Path(__file__).with_name("remediation_audit.jsonl")
display = st.session_state.get("investigation_display")
current_investigation_id = (
    display.get("investigation_id") if display else None
)


def extract_audit_details(record):
    """Return audit details as a dictionary without assuming a fixed schema."""
    details = record.get("details", {})
    return details if isinstance(details, dict) else {}


def audit_matches_investigation(record, investigation_id):
    """Match only explicit investigation-ID fields; never infer a match."""
    if not investigation_id:
        return False

    details = extract_audit_details(record)

    possible_ids = [
        record.get("investigation_id"),
        details.get("investigation_id"),
        record.get("related_investigation_id"),
        details.get("related_investigation_id"),
    ]

    return investigation_id in possible_ids


def audit_display_value(value):
    """Format nested audit values for a compact table."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


if audit_file.exists():
    try:
        with audit_file.open("r", encoding="utf-8") as file:
            audit_lines = [
                line.strip()
                for line in file
                if line.strip()
            ]
    except OSError as exc:
        audit_lines = []
        st.error(f"Could not read the audit log: {exc}")

    audit_records = []
    invalid_count = 0

    for line in audit_lines:
        try:
            record = json.loads(line)
            if isinstance(record, dict):
                audit_records.append(record)
            else:
                invalid_count += 1
        except json.JSONDecodeError:
            invalid_count += 1

    audit_records.reverse()

    if invalid_count:
        st.warning(
            f"{invalid_count} invalid audit record(s) were skipped."
        )

    if audit_records:
        st.caption(
            f"{len(audit_records)} valid audit event(s) loaded. "
            "The source file is left unchanged."
        )

        filter_options = [
            "All events",
            "Current investigation only",
        ]

        selected_filter = st.radio(
            "Audit history filter",
            options=filter_options,
            horizontal=True,
            key="audit_history_filter",
            disabled=current_investigation_id is None,
            help=(
                "Investigation filtering uses explicit IDs stored in audit "
                "records. Older events without an ID are not assigned to "
                "the current investigation."
            ),
        )

        if selected_filter == "Current investigation only":
            filtered_records = [
                record
                for record in audit_records
                if audit_matches_investigation(
                    record,
                    current_investigation_id,
                )
            ]

            st.caption(
                f"Current investigation: {current_investigation_id}"
            )

            if not filtered_records:
                st.info(
                    "No audit events explicitly reference this investigation. "
                    "Existing records may not store an investigation ID. "
                    "Choose 'All events' to view the complete available history."
                )
        else:
            filtered_records = audit_records

        if filtered_records:
            table_rows = []

            for record in filtered_records:
                details = extract_audit_details(record)

                timestamp = record.get(
                    "timestamp",
                    record.get("created_at", ""),
                )

                table_rows.append({
                    "Timestamp": audit_display_value(timestamp),
                    "Event": audit_display_value(
                        record.get("event", "unknown")
                    ),
                    "Investigation ID": audit_display_value(
                        record.get("investigation_id")
                        or details.get("investigation_id")
                        or record.get("related_investigation_id")
                        or details.get("related_investigation_id")
                        or "Not recorded"
                    ),
                    "Action ID": audit_display_value(
                        record.get("action_id")
                        or details.get("action_id")
                        or "Not recorded"
                    ),
                    "Approval outcome": audit_display_value(
                        record.get("approval_status")
                        or details.get("approval_status")
                        or "—"
                    ),
                    "Executed": audit_display_value(
                        record.get("executed")
                        if "executed" in record
                        else details.get("executed", "Not recorded")
                    ),
                })

            st.dataframe(
                table_rows,
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("View raw audit records"):
            st.json(filtered_records)

    else:
        st.info("No valid audit events recorded yet.")
else:
    st.info("The audit log has not been created yet.")
