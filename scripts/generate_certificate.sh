#!/bin/bash
# Script to generate X.509 certificate for Azure AD App-Only authentication

set -e

echo "========================================="
echo "Azure AD Certificate Generator"
echo "========================================="
echo ""

# Configuration
CERT_DIR="./certificates"
PRIVATE_KEY="$CERT_DIR/sharepoint-private-key.pem"
CERTIFICATE="$CERT_DIR/sharepoint-certificate.pem"
CERTIFICATE_CER="$CERT_DIR/sharepoint-certificate.cer"
CSR="$CERT_DIR/sharepoint.csr"
SECRETS_FILE="$CERT_DIR/secrets-azure-ad.json"

# Certificate details
COUNTRY="US"
STATE="State"
CITY="City"
ORG="Organization"
CN="SharePoint Kendra Connector"
VALIDITY_DAYS=365

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --country)
      COUNTRY="$2"
      shift 2
      ;;
    --state)
      STATE="$2"
      shift 2
      ;;
    --city)
      CITY="$2"
      shift 2
      ;;
    --org)
      ORG="$2"
      shift 2
      ;;
    --cn)
      CN="$2"
      shift 2
      ;;
    --days)
      VALIDITY_DAYS="$2"
      shift 2
      ;;
    --key-size)
      KEY_SIZE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--country US] [--state State] [--city City] [--org Organization] [--cn CommonName] [--days 365] [--key-size 2048]"
      exit 1
      ;;
  esac
done

# Default key size
KEY_SIZE=${KEY_SIZE:-2048}

# Check if OpenSSL is installed
if ! command -v openssl &> /dev/null; then
    echo "✗ OpenSSL is not installed"
    echo "  Install with: brew install openssl (macOS) or apt-get install openssl (Linux)"
    exit 1
fi

echo "Certificate Configuration:"
echo "  Country: $COUNTRY"
echo "  State: $STATE"
echo "  City: $CITY"
echo "  Organization: $ORG"
echo "  Common Name: $CN"
echo "  Validity: $VALIDITY_DAYS days"
echo "  Key Size: $KEY_SIZE bits"
echo ""

# Create certificates directory
mkdir -p "$CERT_DIR"

# Generate private key
echo "Step 1: Generating private key..."
openssl genrsa -out "$PRIVATE_KEY" $KEY_SIZE
echo "✓ Private key generated: $PRIVATE_KEY"
echo ""

# Generate certificate signing request (CSR)
echo "Step 2: Generating certificate signing request..."
openssl req -new -key "$PRIVATE_KEY" -out "$CSR" \
  -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/CN=$CN"
echo "✓ CSR generated: $CSR"
echo ""

# Generate self-signed certificate
echo "Step 3: Generating self-signed certificate..."
openssl x509 -req -days $VALIDITY_DAYS -in "$CSR" \
  -signkey "$PRIVATE_KEY" \
  -out "$CERTIFICATE"
echo "✓ Certificate generated: $CERTIFICATE"
echo ""

# Convert certificate to CER format (for Azure AD upload)
echo "Step 4: Converting certificate to CER format..."
openssl x509 -in "$CERTIFICATE" -outform DER -out "$CERTIFICATE_CER"
echo "✓ CER certificate generated: $CERTIFICATE_CER"
echo ""

# Display certificate information
echo "Step 5: Certificate Information"
echo "----------------------------------------"
openssl x509 -in "$CERTIFICATE" -text -noout | grep -A 2 "Subject:"
openssl x509 -in "$CERTIFICATE" -text -noout | grep -A 2 "Validity"
openssl x509 -in "$CERTIFICATE" -text -noout | grep "Signature Algorithm"
echo ""

# Get certificate thumbprint
THUMBPRINT=$(openssl x509 -in "$CERTIFICATE" -fingerprint -noout | sed 's/SHA1 Fingerprint=//')
echo "Certificate Thumbprint: $THUMBPRINT"
echo ""

# Create secrets template
echo "Step 6: Creating secrets template..."

# Read certificate and private key, format for JSON
CERT_CONTENT=$(cat "$CERTIFICATE" | sed 's/$/\\n/' | tr -d '\n' | sed 's/\\n$//')
KEY_CONTENT=$(cat "$PRIVATE_KEY" | sed 's/$/\\n/' | tr -d '\n' | sed 's/\\n$//')

cat > "$SECRETS_FILE" << EOF
{
  "auth_type": "azure_ad",
  "site_url": "https://YOUR_TENANT.sharepoint.com/sites/YOUR_SITE",
  "client_id": "YOUR_CLIENT_ID_FROM_AZURE_AD",
  "tenant_id": "YOUR_TENANT_ID_FROM_AZURE_AD",
  "certificate": "$CERT_CONTENT",
  "private_key": "$KEY_CONTENT"
}
EOF

echo "✓ Secrets template created: $SECRETS_FILE"
echo ""

echo "========================================="
echo "Certificate Generation Complete!"
echo "========================================="
echo ""
echo "Generated Files:"
echo "  1. Private Key (KEEP SECRET):  $PRIVATE_KEY"
echo "  2. Certificate (PEM):          $CERTIFICATE"
echo "  3. Certificate (CER):          $CERTIFICATE_CER"
echo "  4. Secrets Template:           $SECRETS_FILE"
echo ""
echo "Next Steps:"
echo ""
echo "1. Upload Certificate to Azure AD:"
echo "   - Go to Azure Portal → Azure AD → App registrations"
echo "   - Select your app → Certificates & secrets"
echo "   - Upload: $CERTIFICATE_CER"
echo ""
echo "2. Update Secrets Template:"
echo "   - Edit: $SECRETS_FILE"
echo "   - Replace YOUR_TENANT, YOUR_SITE, YOUR_CLIENT_ID, YOUR_TENANT_ID"
echo "   - Save the file"
echo ""
echo "3. Upload Secrets to AWS:"
echo "   python scripts/setup_secrets.py --file $SECRETS_FILE"
echo ""
echo "4. Deploy Infrastructure:"
echo "   cd infrastructure && cdk deploy --all -c auth_type=azure_ad"
echo ""
echo "⚠️  SECURITY WARNING:"
echo "   - Keep $PRIVATE_KEY secure and never commit to version control"
echo "   - Add $CERT_DIR to .gitignore"
echo "   - Delete local copies after uploading to AWS Secrets Manager"
echo ""
