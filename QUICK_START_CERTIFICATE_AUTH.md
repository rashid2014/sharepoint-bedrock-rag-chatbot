# Quick Start: Certificate-Based Authentication

This is a streamlined guide to get started with Azure AD certificate-based authentication for the SharePoint Bedrock RAG Chatbot.

## Prerequisites

- Azure AD admin access
- AWS account with CLI configured
- OpenSSL installed
- Node.js 18+ and npm

## 5-Minute Setup

### Step 1: Generate Certificate (2 minutes)

```bash
# Clone and navigate to project
cd sharepoint-bedrock-rag-chatbot

# Generate certificate
chmod +x scripts/generate_certificate.sh
bash scripts/generate_certificate.sh --org "Your Company" --days 365
```

**Output**: Creates `certificates/` folder with:
- `sharepoint-certificate.cer` (for Azure AD)
- `secrets-azure-ad.json` (template to fill)

### Step 2: Azure AD Setup (2 minutes)

1. Go to [Azure Portal](https://portal.azure.com) → Azure AD → App registrations
2. Click **New registration**
   - Name: `SharePoint Kendra Connector`
   - Click **Register**
3. **Copy** Application (client) ID and Directory (tenant) ID
4. Go to **Certificates & secrets** → **Certificates** tab
5. Click **Upload certificate** → Select `certificates/sharepoint-certificate.cer`
6. Go to **API permissions** → **Add a permission** → **SharePoint**
7. Select **Application permissions** → Add `Sites.Read.All`
8. Click **Grant admin consent**

### Step 3: Configure Secrets (1 minute)

Edit `certificates/secrets-azure-ad.json`:

```json
{
  "auth_type": "azure_ad",
  "site_url": "https://YOUR_TENANT.sharepoint.com/sites/YOUR_SITE",
  "client_id": "PASTE_CLIENT_ID_HERE",
  "tenant_id": "PASTE_TENANT_ID_HERE",
  "certificate": "...",  // Already filled by script
  "private_key": "..."   // Already filled by script
}
```

Upload to AWS:

```bash
python scripts/setup_secrets.py --file certificates/secrets-azure-ad.json
```

### Step 4: Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build
cdk bootstrap  # First time only
cdk deploy --all -c auth_type=azure_ad
```

### Step 5: Trigger Sync

```bash
python scripts/trigger_sync.py --wait
```

## Verify It Works

```bash
# Check sync status
aws kendra describe-data-source-sync-job \
  --index-id <your-index-id> \
  --id <your-data-source-id> \
  --sync-job-id <your-sync-job-id>

# Check CloudWatch logs
aws logs tail /aws/kendra/sharepoint-genai-index --follow
```

## Deploy Frontend

```bash
cd frontend
cp .env.example .env
# Edit .env with API endpoint from CDK output
npm install
npm run build
npx serve -s build
```

Open http://localhost:3000 and start chatting!

## Troubleshooting

### "Authentication failed"

**Check**:
1. Client ID and Tenant ID are correct
2. Certificate was uploaded to Azure AD
3. Admin consent was granted for API permissions
4. Certificate hasn't expired: `openssl x509 -in certificates/sharepoint-certificate.pem -noout -enddate`

### "Insufficient permissions"

**Fix**:
1. Go to Azure AD → App registrations → Your app
2. API permissions → Grant admin consent
3. Wait 5-10 minutes for propagation

### "Certificate validation failed"

**Fix**:
1. Regenerate certificate: `bash scripts/generate_certificate.sh`
2. Re-upload to Azure AD
3. Update secrets: `python scripts/setup_secrets.py --file certificates/secrets-azure-ad.json`

## Security Checklist

- [ ] Certificate uploaded to Azure AD
- [ ] Private key stored only in AWS Secrets Manager
- [ ] Local certificate files deleted after upload
- [ ] `certificates/` folder added to .gitignore
- [ ] Admin consent granted for API permissions
- [ ] Certificate expiration date noted (set reminder for rotation)

## Next Steps

- Read [Full Authentication Guide](docs/AZURE_AD_CERTIFICATE_AUTH.md)
- Review [Authentication Flow](docs/AUTHENTICATION_FLOW.md)
- Check [Deployment Guide](docs/DEPLOYMENT.md)
- Set up [Monitoring](docs/OPERATIONS.md)

## Support

- **Certificate issues**: See [AZURE_AD_CERTIFICATE_AUTH.md](docs/AZURE_AD_CERTIFICATE_AUTH.md)
- **Kendra issues**: Check CloudWatch logs
- **Deployment issues**: See [DEPLOYMENT.md](docs/DEPLOYMENT.md)
