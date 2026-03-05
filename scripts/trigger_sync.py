#!/usr/bin/env python3
"""
Script to trigger Kendra data source sync job.

Usage:
    python trigger_sync.py
    python trigger_sync.py --index-id your-index-id --data-source-id your-ds-id
"""
import argparse
import boto3
import time
from botocore.exceptions import ClientError


def get_stack_outputs(stack_name: str, region: str) -> dict:
    """Get outputs from CloudFormation stack."""
    client = boto3.client("cloudformation", region_name=region)
    
    try:
        response = client.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        return {o["OutputKey"]: o["OutputValue"] for o in outputs}
    except ClientError as e:
        print(f"✗ Error getting stack outputs: {e}")
        return {}


def start_sync_job(index_id: str, data_source_id: str, region: str) -> str:
    """Start Kendra data source sync job."""
    client = boto3.client("kendra", region_name=region)
    
    try:
        response = client.start_data_source_sync_job(
            Id=data_source_id,
            IndexId=index_id
        )
        execution_id = response["ExecutionId"]
        print(f"✓ Sync job started")
        print(f"  Execution ID: {execution_id}")
        return execution_id
    except ClientError as e:
        print(f"✗ Error starting sync job: {e}")
        raise


def check_sync_status(index_id: str, data_source_id: str, execution_id: str, region: str) -> str:
    """Check status of sync job."""
    client = boto3.client("kendra", region_name=region)
    
    try:
        response = client.describe_data_source_sync_job(
            Id=data_source_id,
            IndexId=index_id,
            ExecutionId=execution_id
        )
        return response["Status"]
    except ClientError as e:
        print(f"✗ Error checking sync status: {e}")
        return "UNKNOWN"


def wait_for_sync_completion(index_id: str, data_source_id: str, execution_id: str, region: str) -> None:
    """Wait for sync job to complete."""
    print("\nWaiting for sync to complete...")
    print("This may take several minutes depending on the number of documents...")
    
    while True:
        status = check_sync_status(index_id, data_source_id, execution_id, region)
        
        if status == "SUCCEEDED":
            print("\n✓ Sync completed successfully!")
            break
        elif status == "FAILED":
            print("\n✗ Sync failed!")
            break
        elif status == "STOPPING" or status == "STOPPED":
            print("\n✗ Sync was stopped!")
            break
        else:
            print(f"  Status: {status}...", end="\r")
            time.sleep(10)


def main():
    parser = argparse.ArgumentParser(
        description="Trigger Kendra data source sync job"
    )
    parser.add_argument(
        "--index-id",
        help="Kendra index ID (will be retrieved from stack if not provided)"
    )
    parser.add_argument(
        "--data-source-id",
        help="Data source ID (will be retrieved from stack if not provided)"
    )
    parser.add_argument(
        "--stack-name",
        default="SharePointBedrockChatbot",
        help="CloudFormation stack name (default: SharePointBedrockChatbot)"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for sync to complete"
    )
    
    args = parser.parse_args()
    
    try:
        # Get IDs from stack outputs if not provided
        if not args.index_id or not args.data_source_id:
            print("Retrieving IDs from CloudFormation stack...")
            outputs = get_stack_outputs(args.stack_name, args.region)
            
            if not outputs:
                print("✗ Could not retrieve stack outputs")
                print("  Please provide --index-id and --data-source-id manually")
                exit(1)
            
            index_id = args.index_id or outputs.get("KendraIndexId")
            data_source_id = args.data_source_id or outputs.get("DataSourceId")
            
            if not index_id or not data_source_id:
                print("✗ Could not find required IDs in stack outputs")
                print("  Please provide --index-id and --data-source-id manually")
                exit(1)
        else:
            index_id = args.index_id
            data_source_id = args.data_source_id
        
        print(f"Index ID: {index_id}")
        print(f"Data Source ID: {data_source_id}")
        print("")
        
        # Start sync job
        execution_id = start_sync_job(index_id, data_source_id, args.region)
        
        # Wait for completion if requested
        if args.wait:
            wait_for_sync_completion(index_id, data_source_id, execution_id, args.region)
        else:
            print("\nSync job started. Check AWS Console for progress.")
            print(f"To wait for completion, run with --wait flag")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
