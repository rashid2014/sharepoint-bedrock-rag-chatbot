#!/usr/bin/env python3
"""
Script to setup SharePoint credentials in AWS Secrets Manager.

Usage:
    python setup_secrets.py --file secrets.json
    python setup_secrets.py --file secrets.json --secret-name custom-secret-name
"""
import json
import argparse
import boto3
from botocore.exceptions import ClientError


def validate_credentials(credentials: dict) -> None:
    """
    Validate credentials based on auth_type.
    
    Args:
        credentials: Dictionary containing credentials
    
    Raises:
        ValueError: If required fields are missing
    """
    auth_type = credentials.get("auth_type")
    
    if not auth_type:
        raise ValueError("auth_type is required")
    
    # Common required fields
    if "site_url" not in credentials:
        raise ValueError("site_url is required")
    
    # Validate based on auth type
    if auth_type == "oauth2":
        required = ["client_id", "client_secret", "tenant_id", "username", "password"]
        missing = [f for f in required if f not in credentials]
        if missing:
            raise ValueError(f"OAuth2 authentication requires: {', '.join(missing)}")
    
    elif auth_type == "azure_ad":
        required = ["client_id", "tenant_id", "certificate", "private_key"]
        missing = [f for f in required if f not in credentials]
        if missing:
            raise ValueError(f"Azure AD App-Only authentication requires: {', '.join(missing)}")
    
    elif auth_type == "sharepoint_app":
        required = ["sharepoint_client_id", "sharepoint_client_secret", "client_id", "client_secret"]
        missing = [f for f in required if f not in credentials]
        if missing:
            raise ValueError(f"SharePoint App-Only authentication requires: {', '.join(missing)}")
    
    elif auth_type == "basic":
        required = ["username", "password"]
        missing = [f for f in required if f not in credentials]
        if missing:
            raise ValueError(f"Basic authentication requires: {', '.join(missing)}")
    
    else:
        raise ValueError(f"Invalid auth_type: {auth_type}. Must be one of: oauth2, azure_ad, sharepoint_app, basic")


def create_or_update_secret(secret_name: str, credentials: dict, region: str = "us-east-1") -> None:
    """
    Create or update secret in AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret
        credentials: Dictionary containing credentials
        region: AWS region
    """
    client = boto3.client("secretsmanager", region_name=region)
    
    try:
        # Try to update existing secret
        response = client.put_secret_value(
            SecretId=secret_name,
            SecretString=json.dumps(credentials)
        )
        print(f"✓ Successfully updated secret: {secret_name}")
        print(f"  ARN: {response['ARN']}")
        print(f"  Version: {response['VersionId']}")
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            # Secret doesn't exist, create it
            print(f"Secret not found. Creating new secret: {secret_name}")
            response = client.create_secret(
                Name=secret_name,
                Description="SharePoint authentication credentials for Kendra connector",
                SecretString=json.dumps(credentials)
            )
            print(f"✓ Successfully created secret: {secret_name}")
            print(f"  ARN: {response['ARN']}")
        else:
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Setup SharePoint credentials in AWS Secrets Manager"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to JSON file containing credentials"
    )
    parser.add_argument(
        "--secret-name",
        default="sharepoint-chatbot/credentials",
        help="Name of the secret in Secrets Manager (default: sharepoint-chatbot/credentials)"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    
    args = parser.parse_args()
    
    try:
        # Read credentials from file
        print(f"Reading credentials from: {args.file}")
        with open(args.file, "r") as f:
            credentials = json.load(f)
        
        # Validate credentials
        print("Validating credentials...")
        validate_credentials(credentials)
        print("✓ Credentials are valid")
        
        # Create or update secret
        print(f"\nCreating/updating secret in AWS Secrets Manager...")
        create_or_update_secret(args.secret_name, credentials, args.region)
        
        print("\n✓ Setup complete!")
        print(f"\nNext steps:")
        print(f"1. Deploy CDK infrastructure: cd infrastructure && cdk deploy")
        print(f"2. Trigger initial sync: python scripts/trigger_sync.py")
        
    except FileNotFoundError:
        print(f"✗ Error: File not found: {args.file}")
        print(f"  Create a credentials file from one of the templates in templates/")
        exit(1)
    
    except ValueError as e:
        print(f"✗ Validation error: {e}")
        exit(1)
    
    except ClientError as e:
        print(f"✗ AWS error: {e}")
        exit(1)
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
