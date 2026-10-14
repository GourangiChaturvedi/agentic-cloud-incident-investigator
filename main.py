
import json

from diagnostic_tools import (
    analyze_logs,
    search_logs,
    get_cpu_metrics,
    get_database_metrics,
    get_recent_deployments
)

def check_cpu(cpu_usage):
    if cpu_usage > 90:
        return "High CPU detected"
    return "CPU is normal"


def check_database_connections(connections):
    if connections > 80:
        return "High database connections detected"
    return "Database connections are normal"



try:
    with open("data/incident.json", "r") as file:
        incident = json.load(file)

    
    if not isinstance(incident, dict):
        raise ValueError("Incident data must be a JSON object.")

    required_fields = [
        "incident_id",
        "incident_type",
        "cpu_usage_percent",
        "database_connections",
        "recent_deployment",
        "logs"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in incident
    ]

    if missing_fields:
        raise ValueError(
            "Missing incident fields: " + ", ".join(missing_fields)
        )

    if not isinstance(incident["logs"], list):
        raise ValueError("Incident logs must be a list.")


    print("Incident ID:", incident["incident_id"])
    print("Incident Type:", incident["incident_type"])
    print("CPU Usage:", incident["cpu_usage_percent"], "%")
    print("CPU Assessment:", check_cpu(incident["cpu_usage_percent"]))
    print(
    "Database Assessment:",
    check_database_connections(incident["database_connections"])
)
    print("Recent Deployment:", incident["recent_deployment"])

    print("\nIncident Logs:")
    for log in incident["logs"]:
        print("-", log)
    
    
    print("\nLog Analysis:")
    log_analysis = analyze_logs(incident["logs"])

    if log_analysis.get("status") == "success":
     for finding in log_analysis.get("findings", []):
        print("-", finding)

     if log_analysis.get("skipped_entries", 0) > 0:
        print(
            "Skipped invalid log entries:",
            log_analysis["skipped_entries"]
        )
    else:
       print(
        "Log analysis error:",
        log_analysis.get("message", "Unknown log analysis error.")
    )



except FileNotFoundError:
    print("Error: Incident file not found.")

except json.JSONDecodeError:
    print("Error: Invalid JSON format.")

except KeyError as error:
    import traceback
    traceback.print_exc()

except ValueError as error:
    print("Error: Invalid incident data:", error)