#!/bin/bash
# Deployment script for SharePoint Bedrock RAG Chatbot infrastructure

set -e  # Exit on error

echo "========================================="
echo "SharePoint Bedrock RAG Chatbot Deployment"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "✗ Node.js is not installed"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "✗ npm is not installed"
    exit 1
fi

if ! command -v cdk &> /dev/null; then
    echo "✗ AWS CDK is not installed. Install with: npm install -g aws-cdk"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "✗ AWS CLI is not installed"
    exit 1
fi

echo "✓ Prerequisites check passed"
echo ""

# Navigate to infrastructure directory
cd "$(dirname "$0")/../infrastructure"

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install
echo "✓ Dependencies installed"
echo ""

# Build TypeScript
echo "Building TypeScript..."
npm run build
echo "✓ TypeScript compiled"
echo ""

# Bootstrap CDK (if needed)
echo "Checking CDK bootstrap status..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    echo "CDK not bootstrapped. Running bootstrap..."
    cdk bootstrap
    echo "✓ CDK bootstrapped"
else
    echo "✓ CDK already bootstrapped"
fi
echo ""

# Synthesize CloudFormation templates
echo "Synthesizing CloudFormation templates..."
cdk synth
echo "✓ Templates synthesized"
echo ""

# Deploy stacks
echo "Deploying stacks..."
echo "This may take 10-15 minutes..."
cdk deploy --all --require-approval never

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""

# Get stack outputs
echo "Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name SharePointBedrockChatbot \
    --query 'Stacks[0].Outputs' \
    --output table

echo ""
echo "Next steps:"
echo "1. Setup SharePoint credentials: python scripts/setup_secrets.py --file secrets.json"
echo "2. Trigger initial sync: python scripts/trigger_sync.py"
echo "3. Deploy frontend: bash scripts/deploy_frontend.sh"
