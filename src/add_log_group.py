#!/usr/bin/env python3
import boto3
import sys
import json
from datetime import datetime
import re

def get_all_log_groups():
    """Get all CloudWatch log groups with pagination support"""
    logs_client = boto3.client('logs')
    log_groups = []
    next_token = None
    
    while True:
        params = {'limit': 50}
        if next_token:
            params['nextToken'] = next_token
            
        response = logs_client.describe_log_groups(**params)
        log_groups.extend(response.get('logGroups', []))
        
        next_token = response.get('nextToken')
        if not next_token:
            break
            
    return log_groups

def display_log_groups(log_groups):
    """Display log groups with indices for selection"""
    print("\nAvailable CloudWatch Log Groups:")
    print("-------------------------------")
    
    for i, log_group in enumerate(log_groups, 1):
        log_group_name = log_group['logGroupName']
        size_mb = log_group.get('storedBytes', 0) / 1024 / 1024
        created = datetime.fromtimestamp(log_group.get('creationTime', 0) / 1000).strftime('%Y-%m-%d')
        
        print(f"{i:3d}. {log_group_name} ({size_mb:.2f} MB, created: {created})")
    
    print("\n")

def get_log_group_selection(log_groups):
    """Prompt user to select log groups and return selected ones"""
    total_count = len(log_groups)
    if total_count == 0:
        print("No log groups found in your AWS account")
        sys.exit(1)
    
    while True:
        selection = input(f"Select log groups (1-{total_count}, comma-separated, 'all', or regex pattern): ")
        
        # Handle 'all' selection
        if selection.lower() == 'all':
            return log_groups
        
        # Check if it's a regex pattern
        if selection.startswith('/') and selection.endswith('/'):
            pattern = selection[1:-1]
            try:
                regex = re.compile(pattern)
                selected_groups = [lg for lg in log_groups if regex.search(lg['logGroupName'])]
                if not selected_groups:
                    print(f"No log groups matched the pattern '{pattern}'")
                    continue
                
                print(f"\nMatched {len(selected_groups)} log groups:")
                for lg in selected_groups:
                    print(f"- {lg['logGroupName']}")
                
                confirm = input("\nConfirm selection (y/n): ")
                if confirm.lower() == 'y':
                    return selected_groups
                continue
            except re.error as e:
                print(f"Invalid regex pattern: {e}")
                continue
        
        # Handle comma-separated indices
        try:
            if ',' in selection:
                indices = [int(idx.strip()) for idx in selection.split(',')]
            else:
                indices = [int(selection.strip())]
            
            selected_groups = []
            for idx in indices:
                if 1 <= idx <= total_count:
                    selected_groups.append(log_groups[idx-1])
                else:
                    print(f"Invalid selection: {idx}. Please enter numbers between 1 and {total_count}")
                    break
            else:
                if selected_groups:
                    print("\nSelected log groups:")
                    for lg in selected_groups:
                        print(f"- {lg['logGroupName']}")
                    
                    confirm = input("\nConfirm selection (y/n): ")
                    if confirm.lower() == 'y':
                        return selected_groups
        except ValueError:
            print("Invalid input. Please enter valid numbers, 'all', or a regex pattern")

def main():
    # Get command line arguments
    if len(sys.argv) < 2:
        print("Error: DynamoDB table name is required")
        print("Usage: python add_log_group.py <DynamoDB-Table-Name>")
        sys.exit(1)
    
    table_name = sys.argv[1]
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    # Get all log groups and display them
    print("Fetching CloudWatch log groups...")
    log_groups = get_all_log_groups()
    display_log_groups(log_groups)
    
    # Get user selection
    selected_log_groups = get_log_group_selection(log_groups)
    
    # Ask for S3 bucket information
    s3_bucket_name = input("\nS3 Bucket Name: ")
    if not s3_bucket_name:
        print("Error: S3 bucket name is required")
        sys.exit(1)
    
    # Ask for optional S3 prefix
    s3_prefix = input("S3 Prefix (optional): ")
    
    # Add each selected log group to DynamoDB
    added_count = 0
    for log_group in selected_log_groups:
        log_group_name = log_group['logGroupName']
        
        # Create the item to insert
        item = {
            'logGroupName': log_group_name,
            's3BucketName': s3_bucket_name,
            'createdAt': datetime.now().isoformat()
        }
        
        # Add optional prefix if provided
        if s3_prefix:
            item['s3Prefix'] = s3_prefix
        
        try:
            # Save to DynamoDB
            table.put_item(Item=item)
            print(f"Added: {log_group_name}")
            added_count += 1
        except Exception as e:
            print(f"Error adding log group {log_group_name}: {str(e)}")
    
    if added_count > 0:
        print(f"\nSuccessfully added {added_count} log group(s) to the configuration")
    else:
        print("\nNo log groups were added to the configuration")

if __name__ == "__main__":
    main()