
from aws_cloudwatch import get_ec2_cpu_metrics


def test_cpu_metrics_result_structure():
    result = get_ec2_cpu_metrics()

    assert result["status"] in ("success", "error")
    assert result["region"] == "ap-southeast-2"
    assert isinstance(result["metrics"], list)
    assert isinstance(result["message"], str)

    print("Status:", result["status"])
    print("Metrics found:", len(result["metrics"]))
    print("Message:", result["message"])


if __name__ == "__main__":
    test_cpu_metrics_result_structure()
