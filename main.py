
import json


def check_cpu(cpu_usage):
    if cpu_usage > 90:
        return "High CPU detected"
    return "CPU is normal"

try:
    with open("data/incident.json", "r") as file:
        incident = json.load(file)

    print("Incident ID:", incident["incident_id"])
    print("Incident Type:", incident["incident_type"])
    print("CPU Usage:", incident["cpu_usage_percent"], "%")
    print("CPU Assessment:", check_cpu(incident["cpu_usage_percent"]))
    print("Recent Deployment:", incident["recent_deployment"])

    print("\nIncident Logs:")
    for log in incident["logs"]:
        print("-", log)

except FileNotFoundError:
    print("Error: Incident file not found.")

except json.JSONDecodeError:
    print("Error: Invalid JSON format.")

except KeyError as error:
    print("Error: Missing incident field:", error)
