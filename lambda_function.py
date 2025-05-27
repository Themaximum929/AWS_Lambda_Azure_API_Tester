import json
import requests
import hashlib
import time 
import boto3
import os
from openai import AzureOpenAI

sns = boto3.client('sns')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN'] 

endpoint = os.environ['AZURE_OPENAI_ENDPOINT']
model_name = os.environ['AZURE_OPENAI_MODEL_NAME'] 
deployment = os.environ['AZURE_OPENAI_DEPLOYMENT']

subscription_key = os.environ['AZURE_OPENAI_KEY']
api_version = os.environ['AZURE_OPENAI_API_VERSION']    

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version=api_version
)

DEFAULT_MESSAGES = json.loads(os.environ.get("TEST_MESSAGES", json.dumps([
    {
        "role": "system",
        "content": f"""
            # 輸出格式 
            請以自然語言對話的方式回應，每次僅回答當前提問即可。
            """
    },
    {
        "role": "user",
        "content": "Whats your chief complains?"
    }  
])))

DEFAULT_REQUETS_COUNT = int(os.environ.get("REQUEST_COUNT", 1))
DEFAULT_TIMEOUT = int(os.environ.get("TIMEOUT", 5))
CHECK_BODY = os.environ.get("CHECK_BODY", "true").lower() == "true"     

def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def lambda_handler(event, context): 
    messages = event.get("messages", DEFAULT_MESSAGES)  
    request_count = event.get("request_count", DEFAULT_REQUETS_COUNT)
    timeout = event.get("timeout", DEFAULT_TIMEOUT)
    check_body = event.get("check_body", CHECK_BODY)

    inconsistencies = []
    slow_responses = [] 
    base_hash = None

    for i in range(request_count):  
        try:
            start_time = time.time()    

            response = client.chat.completions.create(
                messages = messages,
                max_tokens = 1000,
                temperature = 0.1, 
                model = deployment,
            )

            duration = time.time() - start_time 

            content = response.choices[0].message.content.strip()

            if duration > 10.0:
                slow_responses.append({
                    "duration": duration,
                    "request": messages,
                    "response": content
                })
            
            if check_body:
                content_hash = get_hash(content)
                if base_hash is None:
                    base_hash = content_hash
                elif base_hash != content_hash:
                    inconsistencies.append({
                        "index": i,
                        "error": f"Hash mismatch: {base_hash} != {content_hash}"
                    })
        except Exception as e:
            inconsistencies.append({
                "index": i,
                "error": f"Exception: {str(e)}"
            })

    result = {
        "deplyment": deployment,
        "total_requests": request_count,    
        "inconsistencies": inconsistencies,
        "slow_responses": slow_responses,
        "response": content,
    }
    # Print out the result
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if inconsistencies:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(result, indent=2),
            Subject="⚠️ Azure OpenAI Consistency Check Failed"
        )
    
    return {
        "statusCode": 200,
        "body": json.dumps(result, indent=2, ensure_ascii=False)
    }
