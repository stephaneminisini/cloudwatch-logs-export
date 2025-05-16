import boto3
import json
import os
import logging
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch_logs = boto3.client('logs')
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['LOGS_CONFIG_TABLE_NAME']
table = dynamodb.Table(table_name)

# Get export time range from environment variable (default to 1440 minutes = 24 hours if not set)
try:
    EXPORT_TIME_RANGE_MINUTES = int(os.environ.get('EXPORT_TIME_RANGE_MINUTES', '1440'))
except ValueError:
    logger.warning("Invalid EXPORT_TIME_RANGE_MINUTES value, using default of 1440 minutes (24 hours)")
    EXPORT_TIME_RANGE_MINUTES = 1440

def handler(event, context):
    """
    Lambda function to export CloudWatch logs to S3
    Triggered by EventBridge scheduled rule
    """
    try:
        # Get log groups configurations from DynamoDB
        response = table.scan()
        log_configs = response.get('Items', [])
        
        if not log_configs:
            logger.info('No log group configurations found in DynamoDB')
            return {
                'statusCode': 200,
                'body': json.dumps('No log group configurations found')
            }
        
        results = []
        
        for config in log_configs:
            log_group_name = config['logGroupName']
            s3_bucket_name = config['s3BucketName']
            s3_prefix = config.get('s3Prefix')
            
            # Calculate time range for export based on configured minutes
            to_time = int(datetime.now().timestamp() * 1000)
            from_time = int((datetime.now() - timedelta(minutes=EXPORT_TIME_RANGE_MINUTES)).timestamp() * 1000)

            logger.info(f"Exporting logs from {datetime.fromtimestamp(from_time/1000)} to {datetime.fromtimestamp(to_time/1000)}")
            
            # Generate destination prefix if not provided
            if not s3_prefix:
                today = datetime.now().strftime('%Y-%m-%d')
                s3_prefix = f"exports/{log_group_name}/{today}"
            
            export_params = {
                'destination': s3_bucket_name,
                'from': from_time,
                'to': to_time,
                'logGroupName': log_group_name,
                'destinationPrefix': s3_prefix
            }
            
            try:
                logger.info(f"Exporting logs for {log_group_name} to {s3_bucket_name}/{s3_prefix}")
                export_result = cloudwatch_logs.create_export_task(**export_params)
                logger.info(f"Export task created: {export_result['taskId']}")
                
                results.append({
                    'logGroupName': log_group_name,
                    'taskId': export_result['taskId'],
                    'status': 'EXPORT_STARTED'
                })
            except Exception as e:
                logger.error(f"Error exporting logs for {log_group_name}: {str(e)}")
                results.append({
                    'logGroupName': log_group_name,
                    'error': str(e),
                    'status': 'EXPORT_FAILED'
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'CloudWatch Logs export process completed',
                'results': results
            })
        }
    
    except Exception as e:
        logger.error(f"Error in lambda execution: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing CloudWatch Logs export',
                'error': str(e)
            })
        }