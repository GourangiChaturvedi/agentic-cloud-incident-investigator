
import boto3

from diagnostic_tools import (
    get_cpu_metrics,
    get_database_metrics,
    analyze_logs,
)

from llm_tool_schema import (
    CPU_TOOL_CONFIG,
    DATABASE_TOOL_CONFIG,
    LOG_TOOL_CONFIG,
)



REGION = "ap-southeast-2"
MODEL_ID = "amazon.nova-lite-v1:0"


TOOL_CONFIG = {
    "tools": (
        CPU_TOOL_CONFIG["tools"]
        + DATABASE_TOOL_CONFIG["tools"]
        + LOG_TOOL_CONFIG["tools"]
    )
}




def main():
    client = boto3.client("bedrock-runtime", region_name=REGION)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                       "Investigate this application incident. Use the "
"analyze_logs tool to inspect these logs: "
"['Repeated request timeouts detected', "
"'Application response time increased', "
"'Database connection failed']. "
"Briefly explain the findings."

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
    **TOOL_CONFIG,
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

    
    
    # Execute the diagnostic tool requested by the model.
    tool_name = tool_use["name"]
    tool_input = tool_use["input"]

    if tool_name == "get_cpu_metrics":
        result = get_cpu_metrics(tool_input["incident"])
    elif tool_name == "get_database_metrics":
        result = get_database_metrics(tool_input["incident"])
    elif tool_name == "analyze_logs":
        result = analyze_logs(tool_input["logs"])
    else:
        raise ValueError(
            f"Unexpected tool requested: {tool_name}"
        )


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
    **TOOL_CONFIG,
    "toolChoice": {"auto": {}},
},
    )

    
    print("\nNova Lite's explanation:")
    for block in final_response["output"]["message"]["content"]:
        if "text" in block:
            text = block["text"].strip()
            
            if "<thinking>" in text and "</thinking>" in text:
                before = text.split("<thinking>", 1)[0]
                after = text.split("</thinking>", 1)[1]
                text = before + after
                text = text.strip()

            if "<response>" in text:
                text = text.split("<response>", 1)[1]
            if "</response>" in text:
                text = text.split("</response>", 1)[0]

            print(text.strip())


if __name__ == "__main__":
    main()
