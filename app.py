
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
    "Investigate cloud incidents using diagnostic evidence "
    "and AI-assisted root-cause analysis."
)

st.divider()

st.subheader("Incident Overview")

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
}

selected_name = st.selectbox(
    "Select a simulated incident",
    list(incidents.keys()),
)

incident = incidents[selected_name]

st.markdown(f"**Incident ID:** `{incident['incident_id']}`")
st.markdown("**Environment:** Simulated incident data")

cpu = incident["cpu_usage_percent"]
db = incident["database_connections"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("CPU Utilization", f"{cpu}%")
    if cpu > 90:
        st.error("High CPU usage")
    else:
        st.success("CPU within threshold")

with col2:
    st.metric("Database Connections", db)
    if db > 80:
        st.error("High database connections")
    else:
        st.success("Database within threshold")

with col3:
    st.metric("Log Entries", len(incident["logs"]))
    if any("timeout" in log.lower() for log in incident["logs"]):
        st.warning("Request timeouts detected")
    else:
        st.success("No timeout messages detected")

st.subheader("Incident Logs")

for log in incident["logs"]:
    st.write(f"• {log}")

st.divider()

if st.button("🔍 Investigate Incident", type="primary"):
    with st.spinner("Collecting diagnostic evidence..."):
        collection_result = collect_diagnostic_evidence(incident)
        investigation = record_investigation(
            incident,
            collection_result,
        )

    st.subheader("Investigation Results")

    if investigation["status"] == "error":
        st.error(investigation["message"])
    else:
        st.write(f"**Status:** {investigation['status'].title()}")
        st.write(
            f"**Successful diagnostic tools:** "
            f"{investigation['successful_tool_count']}"
        )
        st.write(f"**Tool errors:** {investigation['error_count']}")

        st.write("**Diagnostic evidence**")
        st.json(investigation["evidence"])

        if investigation["errors"]:
            st.warning("Some diagnostic tools failed.")
            st.json(investigation["errors"])
