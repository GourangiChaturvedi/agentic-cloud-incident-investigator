
import json

from diagnostic_tools import validate_incident

with open("data/incident.json", "r", encoding="utf-8") as file:
    incident = json.load(file)

result = validate_incident(incident)

print(result)
assert result["status"] == "success"

print("PASS: Existing incident data matches the shared format.")
