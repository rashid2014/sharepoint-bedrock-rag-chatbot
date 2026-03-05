# Deployment Guide

This guide provides step-by-step instructions for deploying the SharePoint Bedrock RAG Chatbot.

## Prerequisites

### Required Tools

- **AWS Account** with Bedrock access enabled
- **AWS CLI** configured with credentials (`aws configure`)
- **Node.js 18+** and npm installed
- **AWS CDK CLI** installed: `npm install -g aws-cdk`
- **Python 3.11+** installed (for backend Lambda and scripts)
- **SharePoint Online** tenant with admin access

### AWS Service Limits

Ensure your AWS account has sufficient limits for:
- Kendra Enterprise Edition index
- Bedrock model access (Claude v2 or similar)
- Lambda functions
- API Gateway endpoints

### SharePoint Prerequisites

Before deployment, configure SharePoint Online:

1. **Disable Security Defaults** in Azure portal (if using OAuth/Azure AD auth)
2. **Disable Multi-Factor Authentication** for the service account
3. **Register Azure AD Application** (for OAuth 2.0 or Azure AD App-Only)
4. **Grant API Permissions** based on authentication method (see SHAREPOINT_SETUP.md)
5. **Note your tenant ID** (for OAuth authentication)

## Deployment Steps

### Step 1: Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd sharepoint-bedrock-rag-chatbot

# Install infrastructure dependencies (TypeScript/CDK)
cd infrastructure
npm install
npm run build
cd ..
```

### Step 2: Configure SharePoint Credentials

Create a credentials file from one of the templates:

```bash
# Copy template based on your authentication method
cp templates/secrets_oauth2.json secrets.json

# Edit secrets.json with your actual credentials
# DO NOT commit this file to version control!
```

**Example for OAuth 2.0:**

```json
{
  "auth_type": "oauth2",
  "site_url": "https://contoso.sharepoint.com/sites/mysite",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "tenant_id": "your-tenant-id",
  "username": "admin@contoso.com",
  "password": "your-password"
}
```

See `templates/` directory for other authentication methods.

### Step 3: Deploy Infrastructure

```bash
# Make deployment script executable
chmod +x scripts/deploy_infrastructure.sh

# Run deployment
bash scripts/deploy_infrastructure.sh
```

This script will:
1. Install Node.js dependencies
2. Build TypeScript code
3. Bootstrap CDK (if needed)
4. Synthesize CloudFormation templates
5. Deploy all stacks (Secrets, Kendra, Bedrock, API Gateway, Lambda)

**Expected deployment time:** 10-15 minutes

### Step 4: Setup Secrets in AWS

After infrastructure deployment, upload your SharePoint credentials:

```bash
python scripts/setup_secrets.py --file secrets.json
```

This creates/updates the secret in AWS Secrets Manager with your credentials.

### Step 5: Trigger Initial Sync

Start the first synchronization of SharePoint documents:

```bash
# Start sync and wait for completion
python scripts/trigger_sync.py --wait

# Or start sync without waiting
python scripts/trigger_sync.py
```

**Note:** Initial sync may take 30 minutes to several hours depending on the number of documents.

Monitor sync progress in AWS Console:
- Navigate to Amazon Kendra
- Select your index
- Go to "Data sources" tab
- Check sync job status

### Step 6: Deploy Frontend

Configure and deploy the React frontend:

```bash
cd frontend

# Copy environment template
cp .env.example .env

# Edit .env and set API endpoint from Step 3 output
# REACT_APP_API_ENDPOINT=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/query

# Install dependencies and build
npm install
npm run build
```

**Deployment Options:**

**Option A: Local Testing**
```bash
npx serve -s build
# Access at http://localhost:3000
```

**Option B: AWS S3 + CloudFront**
```bash
# Create S3 bucket
aws s3 mb s3://your-chatbot-bucket

# Enable static website hosting
aws s3 website s3://your-chatbot-bucket --index-document index.html

# Upload build
aws s3 sync build/ s3://your-chatbot-bucket --acl public-read

# (Optional) Create CloudFront distribution for HTTPS
```

**Option C: Netlify**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=build
```

**Option D: Vercel**
```bash
npm install -g vercel
vercel --prod
```

### Step 7: Test the Application

1. Open the frontend URL in your browser
2. Enter a test query: "What documents are available?"
3. Verify the response includes:
   - Generated answer
   - Source documents with clickable links
   - SharePoint document locations

## Configuration Parameters

### CDK Context Parameters

You can customize deployment by setting CDK context parameters:

```bash
cdk deploy \
  -c sharepoint_site_url="https://your-site.sharepoint.com/sites/mysite" \
  -c auth_type="oauth2" \
  -c enable_acl=false \
  -c sync_schedule="cron(0 2 * * ? *)"
```

**Available Parameters:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `sharepoint_site_url` | SharePoint Online site URL | Required |
| `sharepoint_folders` | List of folders to index | `["Shared Documents"]` |
| `auth_type` | Authentication method | `oauth2` |
| `sync_schedule` | Cron expression for sync | `cron(0 2 * * ? *)` (2 AM daily) |
| `enable_acl` | Enable user-level access control | `false` |

### Environment Variables

**Infrastructure (CDK - TypeScript):**
- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)
- `SHAREPOINT_SITE_URL`: SharePoint site URL
- `AUTH_TYPE`: Authentication method

**Frontend:**
- `REACT_APP_API_ENDPOINT`: API Gateway endpoint URL

**Lambda:**
- `KNOWLEDGE_BASE_ID`: Bedrock Knowledge Base ID (set by CDK)
- `AWS_REGION`: AWS region (set by CDK)
- `LOG_LEVEL`: Logging level (default: INFO)

## Troubleshooting

### CDK Bootstrap Fails

**Error:** "CDK bootstrap failed"

**Solution:**
```bash
# Manually bootstrap with specific account/region
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Secrets Manager Access Denied

**Error:** "Access denied when creating secret"

**Solution:**
- Ensure AWS CLI is configured with correct credentials
- Verify IAM user has `secretsmanager:CreateSecret` permission

### Kendra Sync Fails

**Error:** "Sync job failed"

**Solutions:**
1. Check SharePoint credentials are correct
2. Verify Security Defaults and MFA are disabled
3. Check API permissions in Azure AD
4. Review CloudWatch logs for detailed error messages

### Lambda Timeout

**Error:** "Task timed out after 30 seconds"

**Solutions:**
1. Increase Lambda timeout in `api_stack.py`
2. Reduce number of retrieved documents
3. Check Bedrock service availability

### Frontend Can't Connect to API

**Error:** "Unable to connect to the server"

**Solutions:**
1. Verify API endpoint URL in `.env` is correct
2. Check CORS configuration in API Gateway
3. Ensure API Gateway is deployed to `prod` stage
4. Test API endpoint directly with curl:
   ```bash
   curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/query \
     -H "Content-Type: application/json" \
     -d '{"query": "test"}'
   ```

## Updating the Deployment

### Update Infrastructure

```bash
cd infrastructure
cdk deploy --all
```

### Update Lambda Code

```bash
cd infrastructure
cdk deploy SharePointBedrockChatbot/ApiStack
```

### Update Frontend

```bash
cd frontend
npm run build
# Re-deploy using your chosen method
```

### Update SharePoint Credentials

```bash
python scripts/setup_secrets.py --file secrets.json
```

### Trigger Manual Sync

```bash
python scripts/trigger_sync.py
```

## Cleanup

To remove all deployed resources:

```bash
cd infrastructure
cdk destroy --all
```

**Warning:** This will delete:
- Kendra index and all indexed data
- Bedrock Knowledge Base
- Lambda function
- API Gateway
- Secrets Manager secret (if not retained)

## Cost Estimation

Approximate monthly costs (us-east-1):

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Kendra Enterprise | 1 index | $810/month |
| Bedrock (Claude v2) | 1M tokens | $8-24/month |
| Lambda | 100K invocations | $0.20/month |
| API Gateway | 100K requests | $0.35/month |
| Secrets Manager | 1 secret | $0.40/month |
| CloudWatch Logs | 5 GB | $2.50/month |

**Total:** ~$820-840/month

**Note:** Kendra is the primary cost driver. Consider using Kendra Developer Edition for testing ($1.40/hour when active).

## Next Steps

- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- See [SHAREPOINT_SETUP.md](SHAREPOINT_SETUP.md) for SharePoint configuration
- Check [OPERATIONS.md](OPERATIONS.md) for monitoring and maintenance
- Read [SECURITY.md](SECURITY.md) for security best practices
