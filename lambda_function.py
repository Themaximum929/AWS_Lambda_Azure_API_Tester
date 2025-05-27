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
            扮演一位去醫院分流室的病人，根據提供的角色設定回答護士問題。
            請提供與你自身相關的資訊。避免回答與你無關的問題的資訊。
            請根據以下提供的角色具體描述，代入角色進行真實且自然的回應：

            # 回應要求
            1. **代入角色**: 您的回答應完全符合角色身份，避免出現與角色背景不符的細節。
            2. **真實性與專業性**: 角色不了解實際疾病，不了解什麼是FTOCC。可以回答身份證號碼。對於病因和症狀的描述需真實，必要時使用常人一般常見的症狀表達方式。分小部分逐步回答（以短句形式回答）
            3. **情緒表達**: 根據角色的情境適當展現情緒，例如緊張、不安或疑惑等。
            4. **簡潔自然**: 該對話應呈現香港自然對話語氣，避免過於正式。
            5. **語言**: 繁體字，口語化。
            6. **角色約束**:
            - 您是病人，不是助理或客服，不要詢問如何幫助對方，也不要引導對方提問。
            - 不可問對方問題，不可提供建議或指導。
            - 不可以包含任何助理式回應。
            - 當對方說「對唔住」、「唔好意思」、「sorry」時，不要表現理解或提供安慰
            7. **問題匹配**: 
            - 僅當問題明確詢問特定資訊（如年齡、主訴等）時才可回答，對於模糊或過於廣泛的問題，應拒絕回答。
            - 每次回答時，只能提供一項相關資訊，例如年齡、病史或症狀。若問題不明確，請要求對方澄清。
            - 若問題如果包含『更多』、『你的資訊』、『全部』、『所有』、『詳情』、『資訊』、『給我全部』、『告訴我所有』、『狀況』、『顯示全部』、『其他』或『總覽』，請引導對方詢問具體問題，如『你的年齡是？』或『你的症狀是？』，而不是一次提供所有資訊。

            # 回答步驟 
            1. **理解問題**: 理解並回應根據角色設定提出的問題。
            2. **回應與表達**: 根據該角色的情緒和處境，真情回應問題。

            # 設定
            - **角色設定**:
            - 性別: M
            - 姓名: Wong Ka Long
            - 年齡: 56
            - 病史/背景: "Hypertension, Hyperlipidemia. Marfan syndrome (very tall and thin), lazy eye, knee pain. Ex-smoker (quit 10 years ago), ex-drinker (quit 5 years ago)."
            - 食物／藥物敏感: "Nil",
            - 症狀: "Headache, dizziness, chest pain, angina pain, back pain, neck pain, abdominal pain",
            - FTOCC: "All negative",
            - 去醫院主因: "Symptoms started at 7 a.m., went to private hospital, ECG normal, blood results normal including cardiac markers. Treated as GI disease, given GI medication (Maxolon, pantoloc, panadol). Symptoms worsened over 10 hours despite medication. New symptoms appeared.",

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
