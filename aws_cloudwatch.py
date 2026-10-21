
import boto3
from botocore.exceptions import BotoCoreError, ClientError


def get_cloudwatch_client(region="ap-southeast-2"):
    """Create a CloudWatch client using the configured AWS credentials."""
    return boto3.client("cloudwatch", region_name=region)


def get_ec2_cpu_metrics(region="ap-southeast-2", hours=1):
    """Retrieve recent EC2 CPU metrics when available."""
    from datetime import datetime, timedelta, timezone

    try:
        cloudwatch = get_cloudwatch_client(region)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        response = cloudwatch.list_metrics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
        )

        results = []

        for metric in response.get("Metrics", []):
            dimensions = metric.get("Dimensions", [])
            instance_id = next(
                (
                    item["Value"]
                    for item in dimensions
                    if item["Name"] == "InstanceId"
                ),
                None,
            )

            if not instance_id:
                continue

            statistics = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum"],
            )

            for point in statistics.get("Datapoints", []):
                results.append({
                    "instance_id": instance_id,
                    "timestamp": point["Timestamp"].isoformat(),
                    "average_cpu": point["Average"],
                    "maximum_cpu": point["Maximum"],
                })

        return {
            "status": "success",
            "region": region,
            "metrics": results,
            "message": (
                "CPU metrics retrieved."
                if results
                else "No EC2 CPU metrics available for the requested period."
            ),
        }

    except (BotoCoreError, ClientError) as exc:
        return {
            "status": "error",
            "region": region,
            "metrics": [],
            "message": f"AWS CloudWatch request failed: {exc}",
        }


def get_cloudwatch_logs(log_group_name, region="ap-southeast-2", minutes=60):
    """Retrieve recent events from an existing CloudWatch log group."""
    from datetime import datetime, timedelta, timezone

    if not isinstance(log_group_name, str) or not log_group_name.strip():
        return {
            "status": "error",
            "region": region,
            "log_group": log_group_name,
            "events": [],
            "message": "A non-empty log group name is required.",
        }

    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
        return {
            "status": "error",
            "region": region,
            "log_group": log_group_name,
            "events": [],
            "message": "Minutes must be a positive integer.",
        }

    try:
        logs = boto3.client("logs", region_name=region)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=minutes)

        response = logs.filter_log_events(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            limit=100,
        )

        events = [
            {
                "timestamp": event.get("timestamp"),
                "message": event.get("message", ""),
                "log_stream": event.get("logStreamName"),
            }
            for event in response.get("events", [])
        ]

        return {
            "status": "success" if events else "unavailable",
            "region": region,
            "log_group": log_group_name,
            "events": events,
            "message": (
                "CloudWatch log events retrieved."
                if events
                else "No log events found in the requested period."
            ),
        }


    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")

        if error_code == "ResourceNotFoundException":
            return {
                "status": "unavailable",
                "region": region,
                "log_group": log_group_name,
                "events": [],
                "message": "The requested CloudWatch log group does not exist.",
            }

        return {
            "status": "error",
            "region": region,
            "log_group": log_group_name,
            "events": [],
            "message": f"CloudWatch Logs request failed: {exc}",
        }

    except BotoCoreError as exc:
        return {
            "status": "error",
            "region": region,
            "log_group": log_group_name,
            "events": [],
            "message": f"CloudWatch Logs request failed: {exc}",
        }
