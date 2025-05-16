# CloudWatch Logs Export to S3

This project sets up AWS infrastructure to automatically export CloudWatch logs to an S3 bucket on a schedule (e.g., daily). It also configures S3 to send notifications to an SQS queue when new exported log files are created.

## Features

- Lambda function that exports CloudWatch logs to S3
- DynamoDB table for storing log group export configurations
- EventBridge (CloudWatch Events) scheduled rule to trigger exports
- S3 bucket with lifecycle policies for exported logs
- SQS queue for notifications when new logs are exported
- CloudFormation template for easy deployment

## Setup

### 1. Deploy Infrastructure

Use the CloudFormation template to deploy the required infrastructure:

```bash
aws cloudformation deploy \
  --template-file template/cloudformation.yaml \
  --stack-name cloudwatch-logs-export \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    S3BucketName=your-logs-export-bucket \
    ScheduleExpression="rate(1 day)" \
    ExportTimeRangeMinutes=1440 \
    LambdaTimeout=300 \
    LambdaMemorySize=256
```

### 2. Deploy Lambda Code

Package and deploy the Lambda function:

```bash
# Create a deployment package
mkdir -p dist
cp src/lambda/index.py dist/index.py
cd dist
pip install boto3 -t .
zip -r ../lambda-function.zip *
cd ..

# Upload to Lambda
aws lambda update-function-code \
  --function-name cloudwatch-logs-export-log-export \
  --zip-file fileb://lambda-function.zip
```

### 3. Configure Log Groups to Export

Use the provided script to add log groups to be exported:

```bash
# Install boto3 if needed
pip install boto3

# Make the script executable
chmod +x src/add_log_group.py

# Run the script with the DynamoDB table name
python src/add_log_group.py cloudwatch-logs-export-log-configs
```

You'll be prompted to enter:
- Log Group Name (e.g., `/aws/lambda/my-function`)
- S3 Bucket Name (the bucket you created in the CloudFormation template)
- S3 Prefix (optional, e.g., `exports/my-function/`)

## How It Works

1. The EventBridge scheduled rule triggers the Lambda function based on the configured schedule
2. The Lambda function retrieves log group configurations from DynamoDB
3. For each configured log group, the Lambda creates an export task to the S3 bucket
4. When new files are created in S3, notifications are sent to the SQS queue
5. You can process these notifications as needed (e.g., with another Lambda function)

## Monitoring

You can monitor the export process through:

- CloudWatch Logs for the Lambda function
- CloudWatch Metrics for the Lambda, SQS queue, and S3 bucket
- The SQS queue for notifications of new exports

## Security Considerations

- The S3 bucket has a bucket policy that allows CloudWatch Logs service to write to it
- IAM roles are configured with least privilege permissions
- DynamoDB and S3 are configured with server-side encryption
- S3 lifecycle policies help manage exported logs (transition to Glacier after 90 days)

## Customization

You can customize the following aspects:
- Export schedule (change the EventBridge schedule expression)
- Export time range (how many minutes of logs to export, default: 1440 minutes = 24 hours)
- Lambda memory and timeout
- S3 lifecycle policies
- Log retention periods

### Configurable Parameters

When deploying with CloudFormation, you can adjust these parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| ScheduleExpression | When to run the export (cron or rate expression) | rate(1 day) |
| ExportTimeRangeMinutes | How many minutes of logs to export | 1440 (24 hours) |
| S3BucketName | Name of the S3 bucket | (required) |
| LambdaTimeout | Timeout for the Lambda function in seconds | 300 |
| LambdaMemorySize | Memory size for the Lambda function in MB | 256 |