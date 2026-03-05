#!/bin/bash
# Deployment script for React frontend

set -e  # Exit on error

echo "========================================="
echo "Frontend Deployment"
echo "========================================="
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")/../frontend"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "✗ .env file not found"
    echo "  Copy .env.example to .env and configure API endpoint"
    echo "  cp .env.example .env"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install
echo "✓ Dependencies installed"
echo ""

# Build for production
echo "Building for production..."
npm run build
echo "✓ Build complete"
echo ""

echo "========================================="
echo "Build Complete!"
echo "========================================="
echo ""
echo "Build output is in: frontend/build/"
echo ""
echo "Deployment options:"
echo "1. Deploy to S3 + CloudFront:"
echo "   aws s3 sync build/ s3://your-bucket-name"
echo "   aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths '/*'"
echo ""
echo "2. Deploy to Netlify:"
echo "   netlify deploy --prod --dir=build"
echo ""
echo "3. Deploy to Vercel:"
echo "   vercel --prod"
echo ""
echo "4. Serve locally for testing:"
echo "   npx serve -s build"
