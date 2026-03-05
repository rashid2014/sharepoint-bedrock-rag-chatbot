# SharePoint-Bedrock RAG Chatbot

A GenAI-powered chatbot application that enables users to query documents stored in SharePoint Online using natural language. The system leverages AWS Kendra GenAI Index for document retrieval, AWS Bedrock Knowledge Base for RAG capabilities, and provides a React-based frontend for user interaction.

## Architecture Overview

- **Frontend**: React/Node.js web application with chat interface
- **API Layer**: AWS API Gateway routing requests to backend Lambda
- **Backend**: Python Lambda function orchestrating query processing
- **Knowledge Base**: AWS Bedrock Knowledge Base for RAG capabilities
- **Search Index**: AWS Kendra GenAI Index for document retrieval
- **Data Source**: SharePoint Online via SharePoint Connector V2.0
- **Infrastructure**: AWS CDK (Python) for resource provisioning

## Key Features

✅ Direct SharePoint indexing (no S3 migration)
✅ **Certificate-based authentication** (Azure AD App-Only - Recommended)
✅ Multiple authentication methods (OAuth 2.0, SharePoint App-Only, Basic)
✅ Kendra GenAI Index for Bedrock integration
✅ RAG with source attribution
✅ Serverless architecture
✅ Complete IaC with AWS CDK (TypeScript)
✅ Production-ready error handling
✅ Responsive React UI
✅ Automated deployment scripts

## Prerequisites

- AWS account with Bedrock access enabled
- SharePoint Online tenant with admin access
- Node.js 18+
- Python 3.11+ (for backend Lambda and scripts)
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- AWS CLI configured with credentials

## Project Structure

```
sharepoint-bedrock-rag-chatbot/
├── infrastructure/          # AWS CDK infrastructure code
│   ├── app.py              # CDK app entry point
│   ├── cdk.json            # CDK configuration
│   ├── requirements.txt    # Python dependencies
│   └── stacks/             # CDK stack definitions
├── backend/                # Lambda function code
│   ├── lambda_function.py  # Main handler
│   ├── bedrock_client.py   # Bedrock API wrapper
│   ├── utils.py            # Helper functions
│   └── requirements.txt    # Python dependencies
├── frontend/               # React application
│   ├── public/             # Static assets
│   ├── src/                # React components
│   └── package.json        # Node.js dependencies
├── scripts/                # Deployment and setup scripts
├── templates/              # Configuration templates
├── docs/                   # Documentation
└── tests/                  # Test suites
```

## Quick Start

**🚀 Fast Track**: Follow the [5-Minute Certificate Auth Setup](QUICK_START_CERTIFICATE_AUTH.md)

### 1. Configure SharePoint Credentials (Certificate-Based - Recommended)

Generate X.509 certificate for Azure AD authentication:

```bash
# Generate certificate and private key
chmod +x scripts/generate_certificate.sh
bash scripts/generate_certificate.sh --org "Your Organization" --days 365

# This creates:
# - certificates/sharepoint-certificate.cer (upload to Azure AD)
# - certificates/secrets-azure-ad.json (template to fill)
```

Follow the detailed guide: [Azure AD Certificate Authentication](docs/AZURE_AD_CERTIFICATE_AUTH.md)

**Alternative**: Use OAuth 2.0 or other methods (see templates/ directory)

### 2. Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build
cdk bootstrap
cdk deploy --all
```

### 3. Setup Secrets

```bash
python scripts/setup_secrets.py --file secrets.json
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
# Deploy to your hosting service
```

## Configuration

See `docs/DEPLOYMENT.md` for detailed deployment instructions and configuration options.

## Documentation

- **[Azure AD Certificate Authentication](docs/AZURE_AD_CERTIFICATE_AUTH.md)** - Recommended production setup
- [Architecture](docs/ARCHITECTURE.md) - System architecture and design
- [Deployment Guide](docs/DEPLOYMENT.md) - Step-by-step deployment instructions
- [SharePoint Setup](docs/SHAREPOINT_SETUP.md) - SharePoint configuration guide
- [API Documentation](docs/API.md) - API endpoint reference
- [Operations Guide](docs/OPERATIONS.md) - Monitoring and maintenance
- [Security Guide](docs/SECURITY.md) - Security best practices

## License

MIT License
