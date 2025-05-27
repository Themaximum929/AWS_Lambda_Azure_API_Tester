# Azure API Consistency Checker (AWS Lambda)
This AWS Lambda function periodically sends requests to an Azure OpenAI API to monitor response consistency and latency. It detects anomalies and sends alerts via Amazon SNS.

## Features
- Sends repeated requests to an Azure API endpoint.
- Validates response consistency using content hashing.
- Identifies slow responses exceeding a defined threshold.
- Publishes alerts to an Amazon SNS topic upon detecting inconsistencies.
- Scheduled execution using Amazon EventBridge.

## 1. Deploy the Lambda Function
Ensure your Lambda function includes the necessary dependencies:
- `openai`
- `boto3`
- `requests`
You can package these libraries with your Lambda function or use Lambda layers.

## 2. Configure Environment Variables
Set the following environment variables for your Lambda function:
- `SNS_TOPIC_ARN`: ARN of the SNS topic for alerts.
- `API_URL`: Azure API endpoint URL.
- `PAYLOAD`: JSON payload to send in requests.
- `REQUESTS_COUNT`: Number of requests per execution.
- `TIMEOUT`: Request timeout in seconds.
- `CHECK_BODY`: Set to true to enable response body consistency checks.

## 3. Set Up Amazon SNS
Create an SNS topic to receive alerts:
1. Navigate to the [Amazon SNS Console](https://console.aws.amazon.com/sns/v3/home).
2. Create a new topic (e.g., `AzureApiAlerts`).
3. Create a subscription (e.g., email) to receive notifications.

## 4. Schedule with Amazon EventBridge
Set up a rule to trigger the Lambda function at regular intervals:
1. Go to the [Amazon EventBridge Console](https://console.aws.amazon.com/events/home).
2. Create a new rule with a fixed rate (e.g., every 5 minutes).
3. Set the Lambda function as the target

##  Sample Payload
Here's an example of a test event to invoke the Lambda function manually:
```
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, who won the world series in 2020?"
    }
  ],
  "request_count": 5,
  "timeout": 10,
  "check_body": true
}
```

## References
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
- [Amazon EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
