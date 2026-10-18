
import streamlit as st

from diagnostic_tools import (
    collect_diagnostic_evidence,
    record_investigation,
)

st.set_page_config(
    page_title="Cloud Incident Investigator",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Agentic AI Cloud Incident Investigator")
st.caption(
    "Investigate simulated cloud incidents using diagnostic evidence."
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

cpu = incident["cpu_usage_percent"]
db = incident["database_connections"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("CPU Utilization", f"{cpu}%")
    st.caption("High" if cpu > 90 else "Within threshold")

with col2:
    st.metric("Database Connections", db)
    st.caption("High" if db > 80 else "Within threshold")

with col3:
    st.metric("Log Entries", len(incident["logs"]))

    timeout_count = sum(
        "timeout" in log.lower()
        for log in incident["logs"]
    )

    st.caption(f"{timeout_count} timeout-related entries")

with st.expander("View original incident logs"):
    for log in incident["logs"]:
        st.write(f"• {log}")

st.divider()
st.subheader("Incident Investigation")

# --------------------------------------------------
# Investigation workflow and results
# --------------------------------------------------

if st.button("🔍 Investigate Incident", type="primary"):

    progress = st.progress(
        0,
        text="Validating incident...",
    )

    activity = st.status(
        "Investigation in progress",
        expanded=True,
    )

    try:
        progress.progress(
            10,
            text="Validating incident...",
        )
        activity.write("Validating incident inputs...")

        progress.progress(
            20,
            text="Collecting diagnostic evidence...",
        )
        activity.write("Running CPU metrics check...")

        activity.write("Running database metrics check...")
        activity.write("Checking recent deployments...")
        activity.write("Analyzing incident logs...")

        collection_result = collect_diagnostic_evidence(incident)

        progress.progress(
            75,
            text="Recording investigation results...",
        )
        activity.write("Recording diagnostic evidence...")

        investigation = record_investigation(
            incident,
            collection_result,
        )

        if investigation["status"] == "error":
            raise RuntimeError(investigation["message"])

        progress.progress(
            100,
            text="Investigation finished",
        )

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

        st.error(
            f"Investigation could not be completed: {exc}"
        )
        st.stop()

    # --------------------------------------------------
    # Extract diagnostic evidence
    # --------------------------------------------------

    evidence = investigation["evidence"]
    errors = investigation["errors"]

    cpu_result = next(
        (
            item for item in evidence
            if item.get("tool") == "get_cpu_metrics"
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

    log_result = next(
        (
            item for item in evidence
            if item.get("tool") == "analyze_logs"
        ),
        None,
    )

    cpu_data = (
        cpu_result.get("data", {})
        if cpu_result else {}
    )

    db_data = (
        db_result.get("data", {})
        if db_result else {}
    )

    deployment_data = (
        deployment_result.get("data", {})
        if deployment_result else {}
    )

    log_data = (
        log_result.get("data", {})
        if log_result else {}
    )

    findings = log_data.get("findings", [])

    cpu_high = cpu_data.get("assessment") == "high"
    db_high = db_data.get("assessment") == "high"

    deployment_detected = (
        deployment_data.get("recent_deployment") is True
    )

    log_issue = any(
        finding != "No matching log patterns detected"
        for finding in findings
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
            investigation["successful_tool_count"],
        )

    with summary2:
        st.metric(
            "Tool Errors",
            investigation["error_count"],
        )

    with summary3:
        st.metric(
            "Evidence Sources",
            len(evidence),
        )

    if errors:
        st.warning(
            "The investigation is incomplete because one or more "
            "diagnostic tools failed."
        )

    # --------------------------------------------------
    # Evidence-based diagnosis
    # --------------------------------------------------

    if not evidence:
        st.warning(
            "Inconclusive: insufficient diagnostic evidence "
            "to identify a probable cause."
        )

        cause = "Inconclusive"
        confidence = "Low"
        uncertainty = (
            "No usable diagnostic evidence was collected. "
            "A root cause cannot be established."
        )

    elif errors:
        st.warning(
            "Some diagnostic tools failed. Interpret this "
            "diagnosis cautiously because evidence is incomplete."
        )

        if cpu_high and db_high:
            cause = "Combined CPU and database connection pressure"
            confidence = "Low"

        elif cpu_high:
            cause = "Application or workload CPU saturation"
            confidence = "Low"

        elif db_high:
            cause = "Database connection pressure"
            confidence = "Low"

        else:
            cause = "Inconclusive"
            confidence = "Low"

        uncertainty = (
            "One or more diagnostic tools failed. Additional "
            "evidence is needed to confirm the probable cause."
        )

    elif not cpu_result or not db_result:
        st.warning(
            "Inconclusive: required CPU or database evidence "
            "is missing."
        )

        cause = "Inconclusive"
        confidence = "Low"
        uncertainty = (
            "The required resource metrics are incomplete, "
            "so a reliable diagnosis cannot be established."
        )

    elif cpu_high and db_high:
        st.warning("Multiple resource-pressure signals detected.")

        cause = "Combined CPU and database connection pressure"
        confidence = "Medium"

        uncertainty = (
            "Both resources exceed their configured thresholds. "
            "Further investigation is needed to determine "
            "the initiating cause."
        )

    elif cpu_high:
        st.warning("High CPU utilization detected.")

        cause = "Application or workload CPU saturation"
        confidence = "Medium"

        uncertainty = (
            "High CPU is confirmed, but the available evidence "
            "does not prove what caused the CPU increase."
        )

    elif db_high:
        st.warning("High database connection usage detected.")

        cause = "Database connection pressure"
        confidence = "Medium"

        uncertainty = (
            "Connection usage exceeds the configured threshold. "
            "The evidence does not identify why connections "
            "are accumulating."
        )

    elif not log_issue:
        st.success(
            "No major issue detected by the available checks."
        )

        cause = "No confirmed resource-pressure cause"
        confidence = "Medium"

        uncertainty = (
            "These checks did not detect high CPU, high database "
            "connection usage, or matching log patterns. "
            "They cannot rule out every possible incident."
        )

    else:
        st.warning(
            "An issue may exist, but its cause is unclear."
        )

        cause = "Inconclusive"
        confidence = "Low"

        uncertainty = (
            "The current checks do not provide enough evidence "
            "to identify a probable root cause."
        )

    # --------------------------------------------------
    # Diagnosis summary
    # --------------------------------------------------

    st.markdown("### Diagnosis Summary")

    if cause == "Inconclusive":
        st.warning(f"**Probable Cause:** {cause}")
    elif confidence == "Low":
        st.warning(f"**Probable Cause:** {cause}")
    elif cause == "No confirmed resource-pressure cause":
        st.success(f"**Assessment:** {cause}")
    else:
        st.info(f"**Probable Cause:** {cause}")

    confidence_col, uncertainty_col = st.columns(2)

    with confidence_col:
        st.markdown("**Evidence Confidence**")

        st.metric(
            label="Confidence Level",
            value=confidence,
        )

    with uncertainty_col:
        st.markdown("**Diagnostic Uncertainty**")
        st.write(uncertainty)

    # --------------------------------------------------
    # Evidence panel
    # --------------------------------------------------

    st.divider()
    st.subheader("Diagnostic Evidence")
    st.caption(
    "Review the metrics, log findings, deployment signals, "
    "and complete diagnostic tool results below."
)

    metric_tab, log_tab, deployment_tab, raw_tab = st.tabs(
        [
            "Metrics",
            "Log Findings",
            "Deployment",
            "All Tool Results",
        ]
    )

    with metric_tab:
        metric_col1, metric_col2 = st.columns(2)

        with metric_col1:
            st.markdown("**CPU Metrics**")

            if cpu_result:
                st.json(cpu_data)
            else:
                st.warning("CPU evidence unavailable.")

        with metric_col2:
            st.markdown("**Database Metrics**")

            if db_result:
                st.json(db_data)
            else:
                st.warning("Database evidence unavailable.")

    with log_tab:
        if log_result:
            for finding in findings:
                st.write(f"• {finding}")
        else:
            st.warning("Log analysis evidence unavailable.")

    with deployment_tab:
        if deployment_result:
            st.write(
                "Recent deployment detected."
                if deployment_detected
                else "No recent deployment detected."
            )
        else:
            st.warning(
                "Deployment evidence unavailable."
            )

    with raw_tab:
        if evidence:
            st.json(evidence)
        else:
            st.info("No diagnostic evidence was collected.")

    # --------------------------------------------------
    # Supporting evidence
    # --------------------------------------------------

    st.markdown("### Supporting Evidence")

    support = []

    if cpu_result:
        support.append(
            f"CPU utilization is "
            f"{cpu_data.get('cpu_usage_percent')}% "
            f"({cpu_data.get('assessment', 'unknown')})."
        )

    if db_result:
        support.append(
            f"Database connections are "
            f"{db_data.get('database_connections')} against "
            f"a threshold of {db_data.get('threshold')}."
        )

    if log_result:
        support.extend(findings)

    if deployment_result:
        support.append(
            "A recent deployment was detected."
            if deployment_detected
            else "No recent deployment was detected."
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

    if cpu_high:
        alternatives.append(
            "Increased request volume or an inefficient "
            "application workload."
        )

    if db_high:
        alternatives.append(
            "Slow queries, connection leaks, or insufficient "
            "connection-pool capacity."
        )

    if deployment_detected:
        alternatives.append(
            "The recent deployment may be related, but timing "
            "alone does not establish causation."
        )

    if not cpu_high and not db_high:
        alternatives.append(
            "The incident may involve an unmonitored dependency, "
            "intermittent failure, or a problem not represented "
            "by these simulated signals."
        )

    if alternatives:
        for alternative in alternatives:
            st.write(f"• {alternative}")
    else:
        st.write(
            "• Other causes may exist beyond the signals "
            "collected by the current diagnostic tools."
        )

    # --------------------------------------------------
    # Tool errors
    # --------------------------------------------------

    if errors:
        st.markdown("### Tool Errors")
        st.json(errors)
