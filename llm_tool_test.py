
import boto3

from diagnostic_tools import get_cpu_metrics
from llm_tool_schema import CPU_TOOL_CONFIG


REGION = "ap-southeast-2"
MODEL_ID = "amazon.nova-lite-v1:0"


def main():
    client = boto3.client("bedrock-runtime", region_name=REGION)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Investigate this CPU incident. Use the "
                        "get_cpu_metrics tool to check CPU usage "
                        "for an incident with CPU utilization of 96%. "
                        "Briefly explain the result."
                    )
                }
            ],
        }
    ]

    response = client.converse(
        modelId=MODEL_ID,
        messages=messages,
        inferenceConfig={
            "maxTokens": 120,
            "temperature": 0,
        },
        toolConfig={
            **CPU_TOOL_CONFIG,
            "toolChoice": {"auto": {}},
        },
    )

    assistant_message = response["output"]["message"]
    tool_use = next(
        (
            block["toolUse"]
            for block in assistant_message["content"]
            if "toolUse" in block
        ),
        None,
    )

    if tool_use is None:
        print("The model did not request the diagnostic tool.")
        for block in assistant_message["content"]:
            if "text" in block:
                print(block["text"])
        return

    if tool_use["name"] != "get_cpu_metrics":
        raise ValueError("Unexpected tool requested by the model.")

    # Python executes the diagnostic locally.
    result = get_cpu_metrics(tool_use["input"]["incident"])
    print("Local diagnostic result:", result)

    # Return the diagnostic result to Nova Lite.
    messages.extend(
        [
            {
                "role": "assistant",
                "content": assistant_message["content"],
            },
            {
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"json": result}],
                        }
                    }
                ],
            },
        ]
    )

    final_response = client.converse(
        modelId=MODEL_ID,
        messages=messages,
        inferenceConfig={
            "maxTokens": 120,
            "temperature": 0,
        },
        toolConfig={
            **CPU_TOOL_CONFIG,
            "toolChoice": {"auto": {}},
        },
    )

    print("\nNova Lite's explanation:")
    for block in final_response["output"]["message"]["content"]:
        if "text" in block:
            print(block["text"])


if __name__ == "__main__":
    main()
