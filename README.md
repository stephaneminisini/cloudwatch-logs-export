# CloudWatch Logs Export to S3

This project sets up AWS infrastructure to automatically export CloudWatch logs to an S3 bucket on a schedule (e.g., daily). It also optionally configures S3 to send notifications to an SQS queue when new exported log files are created.

## Features

- Lambda function that exports CloudWatch logs to S3
- DynamoDB table for storing log group export configurations
- EventBridge (CloudWatch Events) scheduled rule to trigger exports
- S3 bucket with lifecycle policies for exported logs
- Optional SQS queue for notifications when new logs are exported
- CloudFormation template for easy deployment
- Interactive log group selection tool

## Setup

### 1. Deploy Infrastructure

The provided deployment script automates the entire setup process:

```bash
# Make the script executable
chmod +x deploy.sh

# Run with required S3 bucket name
./deploy.sh --bucket your-logs-export-bucket

# Run with all optional parameters
./deploy.sh \
  --bucket your-logs-export-bucket \
  --schedule "rate(12 hours)" \
  --time-range 720 \
  --lambda-timeout 600 \
  --memory 512 \
  --region us-west-2 \
  --sqs-notifications false
```

Alternatively, you can deploy manually with the CloudFormation template:

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
    LambdaMemorySize=256 \
    CreateSQSNotifications=true
```

### 2. Configure Log Groups to Export

Use the provided script to select and add log groups to be exported:

```bash
# Make the script executable
chmod +x src/add_log_group.py

# Run the script with the DynamoDB table name
python src/add_log_group.py cloudwatch-logs-export-log-configs
```

The script will:
1. Fetch and display all available CloudWatch log groups
2. Allow you to select log groups by:
   - Individual numbers (e.g., `1, 3, 5`)
   - Typing `all` to select all log groups
   - Using a regex pattern within slashes (e.g., `/lambda/` or `/aws\/lambda\/.*prod/`)
3. Prompt for the S3 bucket name and optional prefix

## How It Works

1. The EventBridge scheduled rule triggers the Lambda function based on the configured schedule
2. The Lambda function retrieves log group configurations from DynamoDB
3. For each configured log group, the Lambda creates an export task to the S3 bucket
4. If SQS notifications are enabled, notifications are sent to the SQS queue when new files are created in S3
5. You can process these notifications as needed (e.g., with another Lambda function)

## Monitoring

You can monitor the export process through:

- CloudWatch Logs for the Lambda function
- CloudWatch Metrics for the Lambda, SQS queue, and S3 bucket
- The SQS queue for notifications of new exports (if enabled)

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
- SQS notifications (enable or disable)
- S3 lifecycle policies
- Log retention periods

### Configurable Parameters

When deploying, you can adjust these parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| ScheduleExpression | When to run the export (cron or rate expression) | rate(1 day) |
| ExportTimeRangeMinutes | How many minutes of logs to export | 1440 (24 hours) |
| S3BucketName | Name of the S3 bucket | (required) |
| LambdaTimeout | Timeout for the Lambda function in seconds | 300 |
| LambdaMemorySize | Memory size for the Lambda function in MB | 256 |
| CreateSQSNotifications | Whether to create SQS queue for S3 notifications | true |