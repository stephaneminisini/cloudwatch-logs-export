#!/bin/bash
set -e

# Variables
STACK_NAME="cloudwatch-logs-export"
S3_BUCKET_NAME=""
SCHEDULE_EXPRESSION="rate(1 day)"
EXPORT_TIME_RANGE_MINUTES=1440
LAMBDA_TIMEOUT=300
LAMBDA_MEMORY_SIZE=256
REGION=$(aws configure get region || echo "us-east-1")
CREATE_SQS_NOTIFICATIONS="true"
AWS_PROFILE=""

# Help message
display_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -b, --bucket BUCKET_NAME     S3 bucket name (required)"
    echo "  -s, --schedule EXPRESSION    Schedule expression (default: rate(1 day))"
    echo "  -t, --time-range MINUTES     Export time range in minutes (default: 1440)"
    echo "  -l, --lambda-timeout SECONDS Lambda timeout in seconds (default: 300)"
    echo "  -m, --memory SIZE            Lambda memory in MB (default: 256)"
    echo "  -r, --region REGION          AWS region (default: from AWS config)"
    echo "  -q, --sqs-notifications      Create SQS notifications (true/false, default: true)"
    echo "  -p, --profile PROFILE        AWS CLI profile to use"
    echo "  -h, --help                   Display this help message"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -b|--bucket)
            S3_BUCKET_NAME="$2"
            shift 2
            ;;
        -s|--schedule)
            SCHEDULE_EXPRESSION="$2"
            shift 2
            ;;
        -t|--time-range)
            EXPORT_TIME_RANGE_MINUTES="$2"
            shift 2
            ;;
        -l|--lambda-timeout)
            LAMBDA_TIMEOUT="$2"
            shift 2
            ;;
        -m|--memory)
            LAMBDA_MEMORY_SIZE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -q|--sqs-notifications)
            CREATE_SQS_NOTIFICATIONS="$2"
            shift 2
            ;;
        -p|--profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        -h|--help)
            display_help
            ;;
        *)
            echo "Unknown option: $1"
            display_help
            ;;
    esac
done

# Validate required parameters
if [ -z "$S3_BUCKET_NAME" ]; then
    echo "Error: S3 bucket name is required"
    display_help
fi

# Validate SQS notifications parameter
if [[ "$CREATE_SQS_NOTIFICATIONS" != "true" && "$CREATE_SQS_NOTIFICATIONS" != "false" ]]; then
    echo "Error: SQS notifications must be either 'true' or 'false'"
    display_help
fi

# Set up AWS CLI profile and region
PROFILE_OPTION=""
if [ -n "$AWS_PROFILE" ]; then
    PROFILE_OPTION="--profile $AWS_PROFILE"
    echo "Using AWS profile: $AWS_PROFILE"
fi

export AWS_DEFAULT_REGION=$REGION

echo "=== CloudWatch Logs Export Deployment ==="
echo "Stack Name: $STACK_NAME"
echo "S3 Bucket: $S3_BUCKET_NAME"
echo "Schedule: $SCHEDULE_EXPRESSION"
echo "Export Time Range: $EXPORT_TIME_RANGE_MINUTES minutes"
echo "Lambda Timeout: $LAMBDA_TIMEOUT seconds"
echo "Lambda Memory: $LAMBDA_MEMORY_SIZE MB"
echo "Create SQS Notifications: $CREATE_SQS_NOTIFICATIONS"
echo "Region: $REGION"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    # Install uv using pip
    pip install uv
fi

# 1. Deploy CloudFormation Template
echo "Deploying CloudFormation stack..."
aws $PROFILE_OPTION cloudformation deploy \
  --template-file template/cloudformation.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    S3BucketName=$S3_BUCKET_NAME \
    ScheduleExpression="$SCHEDULE_EXPRESSION" \
    ExportTimeRangeMinutes=$EXPORT_TIME_RANGE_MINUTES \
    LambdaTimeout=$LAMBDA_TIMEOUT \
    LambdaMemorySize=$LAMBDA_MEMORY_SIZE \
    CreateSQSNotifications=$CREATE_SQS_NOTIFICATIONS

# 2. Get Lambda function name from stack outputs
echo "Getting Lambda function name from stack outputs..."
LAMBDA_FUNCTION_NAME=$(aws $PROFILE_OPTION cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs[?OutputKey=='LogExportLambdaARN'].OutputValue" \
  --output text | cut -d':' -f7)

if [ -z "$LAMBDA_FUNCTION_NAME" ]; then
    echo "Error: Failed to get Lambda function name from stack outputs"
    exit 1
fi

echo "Lambda Function Name: $LAMBDA_FUNCTION_NAME"

# 3. Package and deploy Lambda function code
echo "Packaging Lambda function code..."
rm -rf dist lambda-function.zip
mkdir -p dist
cp src/lambda/index.py dist/index.py
cd dist

# Install dependencies using uv
echo "Installing dependencies with uv..."
uv pip install --no-cache --system boto3 -t .

# Create deployment zip
echo "Creating deployment package..."
zip -r ../lambda-function.zip *
cd ..

# Update Lambda function code
echo "Updating Lambda function code..."
aws $PROFILE_OPTION lambda update-function-code \
  --function-name $LAMBDA_FUNCTION_NAME \
  --zip-file fileb://lambda-function.zip

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "To add log groups to export, run:"
if [ -n "$AWS_PROFILE" ]; then
    echo "AWS_PROFILE=$AWS_PROFILE python src/add_log_group.py ${STACK_NAME}-log-configs"
else
    echo "python src/add_log_group.py ${STACK_NAME}-log-configs"
fi