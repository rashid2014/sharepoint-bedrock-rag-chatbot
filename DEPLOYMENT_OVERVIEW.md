# Deployment Overview

This document provides a high-level overview of the deployment process for the SharePoint-Bedrock RAG Chatbot.

## Quick Start (5 minutes)

Follow `QUICK_START_CERTIFICATE_AUTH.md` for the fastest setup with certificate-based authentication.

## Full Deployment

Follow `docs/DEPLOYMENT.md` for complete step-by-step instructions.

## High-Level Deployment Steps

### 1. Azure AD Setup (One-Time)

- Create App Registration in Entra ID
- Generate certificate using `scripts/generate_certificate.sh`
- Upload public certificate to Azure AD
- Grant Sites.Read.All permissions

### 2. AWS Setup

- Store credentials in Secrets Manager using `scripts/setup_secrets.py`
- Configure AWS CLI with your target account/region

### 3. Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build
cdk bootstrap  # first time only
cdk deploy --all
```

### 4. Trigger Initial Sync

```bash
python scripts/trigger_sync.py
```

### 5. Deploy Frontend

```bash
cd frontend
npm install
npm run build
# Upload to S3 or your hosting platform
```

## Key Documentation Files

- **`QUICK_START_CERTIFICATE_AUTH.md`** - Fast setup guide (5 minutes)
- **`docs/DEPLOYMENT.md`** - Complete deployment guide with detailed instructions
- **`docs/AZURE_AD_CERTIFICATE_AUTH.md`** - Detailed authentication setup
- **`docs/AUTHENTICATION_FLOW.md`** - Technical deep-dive into authentication
- **`docs/diagrams/authentication-flow.md`** - Visual authentication flow diagrams
- **`docs/FAQ.md`** - Troubleshooting and common questions

## What You Get

This project provides a complete, production-ready GenAI chatbot that:

- ✅ Keeps files in SharePoint Online (no S3 migration needed)
- ✅ Uses secure certificate-based authentication with Azure AD
- ✅ Leverages AWS Kendra for intelligent document indexing
- ✅ Integrates with Amazon Bedrock Knowledge Base for RAG
- ✅ Provides a modern React frontend with API Gateway + Lambda backend
- ✅ Includes all infrastructure as code (AWS CDK in TypeScript)
- ✅ Comprehensive documentation and setup scripts

## Prerequisites

Before deployment, ensure you have:

- AWS Account with appropriate permissions
- Azure AD tenant with admin access
- Node.js 18+ and npm
- Python 3.11+
- AWS CLI configured
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Deployment Time

- **Quick Start**: ~5 minutes (certificate generation + secrets setup)
- **Full Infrastructure Deployment**: ~15-20 minutes (CDK stack deployment)
- **Initial Sync**: Varies based on SharePoint document count
- **Total**: ~30-45 minutes for complete setup

## Next Steps

1. Review the prerequisites in `docs/DEPLOYMENT.md`
2. Follow `QUICK_START_CERTIFICATE_AUTH.md` for rapid setup
3. Deploy infrastructure using CDK
4. Verify deployment and test the chatbot
5. Refer to `docs/FAQ.md` for troubleshooting

## Support

For detailed information on any step, refer to the comprehensive documentation in the `docs/` directory.
