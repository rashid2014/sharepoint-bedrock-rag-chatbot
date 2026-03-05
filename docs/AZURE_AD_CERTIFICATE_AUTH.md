# Azure AD Certificate-Based Authentication Setup

This guide explains how to configure Azure AD App-Only authentication with certificate-based signature verification for the SharePoint Kendra connector.

## Overview

Azure AD App-Only authentication uses X.509 certificates for secure, passwordless authentication. This is the **recommended authentication method** for production environments.

### Authentication Flow

1. **Certificate Generation**: Create a self-signed certificate or use a CA-issued certificate
2. **Azure AD Registration**: Register an application in Entra ID (Azure AD)
3. **Public Key Upload**: Upload the certificate's public key to Azure AD
4. **Private Key Storage**: Store the private key securely in AWS Secrets Manager
5. **Token Generation**: Kendra generates a JWT, signs it with the private key
6. **Signature Verification**: Entra ID validates the signature using the uploaded public key
7. **Access Token**: Entra ID issues an access token for SharePoint access

## Prerequisites

- Azure AD tenant with admin access
- OpenSSL installed (for certificate generation)
- AWS account with Secrets Manager access
- SharePoint Online tenant

## Step 1: Generate X.509 Certificate

### Option A: Self-Signed Certificate (Development/Testing)

```bash
# Generate private key (2048-bit RSA)
openssl genrsa -out sharepoint-private-key.pem 2048

# Generate certificate signing request (CSR)
openssl req -new -key sharepoint-private-key.pem -out sharepoint.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=SharePoint Kendra Connector"

# Generate self-signed certificate (valid for 1 year)
openssl x509 -req -days 365 -in sharepoint.csr \
  -signkey sharepoint-private-key.pem \
  -out sharepoint-certificate.pem

# Convert certificate to CER format (for Azure AD upload)
openssl x509 -in sharepoint-certificate.pem -outform DER -out sharepoint-certificate.cer
```

### Option B: CA-Issued Certificate (Production)

For production, obtain a certificate from a trusted Certificate Authority (CA):

1. Generate CSR: `openssl req -new -key sharepoint-private-key.pem -out sharepoint.csr`
2. Submit CSR to your CA
3. Receive signed certificate from CA
4. Convert to CER format if needed

### Certificate Requirements

- **Key Type**: RSA
- **Key Size**: Minimum 2048 bits (4096 recommended for production)
- **Validity**: 1-2 years (plan for rotation)
- **Format**: PEM for private key, CER for Azure AD upload

## Step 2: Register Application in Entra ID (Azure AD)

### 2.1 Create App Registration

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: `SharePoint Kendra Connector`
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: Leave blank (not needed for app-only auth)
5. Click **Register**
6. **Copy the Application (client) ID** - you'll need this
7. **Copy the Directory (tenant) ID** - you'll need this

### 2.2 Upload Certificate

1. In your app registration, go to **Certificates & secrets**
2. Click **Certificates** tab
3. Click **Upload certificate**
4. Upload the `sharepoint-certificate.cer` file
5. Add a description: "Kendra Connector Certificate"
6. Click **Add**
7. **Note the certificate thumbprint** (optional, for verification)

### 2.3 Grant API Permissions

#### Without ACL (Document-level access only)

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **SharePoint**
4. Select **Application permissions**
5. Add the following permissions:
   - `Sites.Read.All` - Read items in all site collections
6. Click **Add permissions**
7. Click **Grant admin consent** (requires admin privileges)

#### With ACL (User-level access control)

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **SharePoint**
4. Select **Application permissions**
5. Add the following permissions:
   - `Sites.FullControl.All` - Required to retrieve ACLs
6. Click **Add permissions**
7. Click **Grant admin consent**

**Note**: For OneNote documents, also add Microsoft Graph permissions:
- `Notes.Read.All` (Application)
- `Sites.Read.All` (Application)

### 2.4 Verify Configuration

Ensure the following are configured:
- ✅ Application (client) ID copied
- ✅ Directory (tenant) ID copied
- ✅ Certificate uploaded to Azure AD
- ✅ API permissions granted
- ✅ Admin consent provided

## Step 3: Prepare Secrets for AWS Secrets Manager

### 3.1 Format Certificate and Private Key

The certificate and private key must be in PEM format with proper line breaks:

```bash
# View certificate (should start with -----BEGIN CERTIFICATE-----)
cat sharepoint-certificate.pem

# View private key (should start with -----BEGIN RSA PRIVATE KEY-----)
cat sharepoint-private-key.pem
```

### 3.2 Create Secrets JSON File

Create a file `secrets-azure-ad.json` with the following structure:

```json
{
  "auth_type": "azure_ad",
  "site_url": "https://contoso.sharepoint.com/sites/mysite",
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "certificate": "-----BEGIN CERTIFICATE-----\nMIIDXTCCAkWgAwIBAgIJAKL...\n-----END CERTIFICATE-----",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
}
```

**Important Notes:**
- Replace `\n` with actual newlines when copying from files
- Ensure no extra spaces or characters
- Keep the BEGIN/END markers
- The certificate is the public key (safe to share with Azure AD)
- The private key must be kept secret (never commit to version control)

### 3.3 Alternative: Use Script to Format

```bash
# Create secrets file with proper formatting
cat > secrets-azure-ad.json << EOF
{
  "auth_type": "azure_ad",
  "site_url": "https://contoso.sharepoint.com/sites/mysite",
  "client_id": "YOUR_CLIENT_ID",
  "tenant_id": "YOUR_TENANT_ID",
  "certificate": "$(cat sharepoint-certificate.pem | sed 's/$/\\n/' | tr -d '\n')",
  "private_key": "$(cat sharepoint-private-key.pem | sed 's/$/\\n/' | tr -d '\n')"
}
EOF
```

## Step 4: Upload Secrets to AWS Secrets Manager

```bash
# Upload secrets using the setup script
python scripts/setup_secrets.py --file secrets-azure-ad.json

# Verify secret was created
aws secretsmanager get-secret-value \
  --secret-id sharepoint-chatbot/credentials \
  --query SecretString \
  --output text | jq .
```

## Step 5: Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build

# Deploy with Azure AD authentication
cdk deploy --all \
  -c auth_type=azure_ad \
  -c sharepoint_site_url="https://contoso.sharepoint.com/sites/mysite"
```

## Step 6: Verify Authentication

### 6.1 Trigger Initial Sync

```bash
python scripts/trigger_sync.py --wait
```

### 6.2 Check CloudWatch Logs

Monitor the Kendra data source sync job logs:

```bash
aws logs tail /aws/kendra/sharepoint-genai-index --follow
```

**Success indicators:**
- ✅ "Authentication successful"
- ✅ "Connected to SharePoint"
- ✅ "Indexing documents..."

**Failure indicators:**
- ❌ "Authentication failed"
- ❌ "Certificate validation failed"
- ❌ "Invalid client credentials"

## Troubleshooting

### Error: "Certificate validation failed"

**Cause**: Certificate format is incorrect or corrupted

**Solution**:
1. Verify certificate format: `openssl x509 -in sharepoint-certificate.pem -text -noout`
2. Ensure proper PEM encoding with line breaks
3. Re-upload certificate to Azure AD
4. Regenerate secrets JSON file

### Error: "Invalid client credentials"

**Cause**: Client ID or Tenant ID is incorrect

**Solution**:
1. Verify Client ID in Azure AD app registration
2. Verify Tenant ID in Azure AD overview
3. Update secrets JSON with correct IDs
4. Re-upload to Secrets Manager

### Error: "Insufficient permissions"

**Cause**: API permissions not granted or admin consent not provided

**Solution**:
1. Go to Azure AD app registration → API permissions
2. Verify required permissions are listed
3. Click "Grant admin consent for [Tenant]"
4. Wait 5-10 minutes for permissions to propagate

### Error: "Certificate expired"

**Cause**: Certificate validity period has ended

**Solution**:
1. Generate new certificate (see Step 1)
2. Upload new certificate to Azure AD
3. Update secrets in Secrets Manager
4. Trigger new sync job

## Security Best Practices

### Certificate Management

1. **Rotation**: Rotate certificates every 12 months
2. **Storage**: Store private keys only in AWS Secrets Manager
3. **Access Control**: Limit Secrets Manager access to Kendra IAM role only
4. **Backup**: Keep encrypted backups of certificates in secure location
5. **Monitoring**: Set up CloudWatch alarms for authentication failures

### Key Size Recommendations

- **Development**: 2048-bit RSA
- **Production**: 4096-bit RSA
- **High Security**: Consider using ECC (Elliptic Curve) certificates

### Certificate Lifecycle

```
┌─────────────┐
│  Generate   │
│ Certificate │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Upload    │
│  to Azure   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Store    │
│  in Secrets │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Monitor   │
│  Expiration │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Rotate    │
│ (12 months) │
└─────────────┘
```

## Certificate Rotation Procedure

### Before Expiration (30 days)

1. Generate new certificate pair
2. Upload new certificate to Azure AD (keep old one active)
3. Update Secrets Manager with new certificate
4. Test authentication with new certificate
5. Remove old certificate from Azure AD after verification

### Automated Rotation (Recommended)

Consider implementing automated certificate rotation using:
- AWS Lambda function triggered by CloudWatch Events
- AWS Certificate Manager (ACM) for certificate management
- Azure Key Vault for certificate storage (alternative)

## Comparison with Other Auth Methods

| Feature | Azure AD App-Only | OAuth 2.0 | Basic Auth |
|---------|-------------------|-----------|------------|
| Security | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Passwordless | ✅ Yes | ❌ No | ❌ No |
| MFA Compatible | ✅ Yes | ❌ No | ❌ No |
| Certificate-based | ✅ Yes | ❌ No | ❌ No |
| Production Ready | ✅ Yes | ⚠️ Conditional | ❌ No |
| Setup Complexity | Medium | Low | Low |
| Maintenance | Low | Medium | High |

**Recommendation**: Use Azure AD App-Only authentication for all production deployments.

## Additional Resources

- [Microsoft: Certificate credentials for application authentication](https://learn.microsoft.com/en-us/azure/active-directory/develop/active-directory-certificate-credentials)
- [AWS Kendra SharePoint Connector V2.0 Documentation](https://docs.aws.amazon.com/kendra/latest/dg/data-source-v2-sharepoint.html)
- [OpenSSL Certificate Commands](https://www.openssl.org/docs/man1.1.1/man1/openssl-x509.html)

## Support

For issues with:
- **Certificate generation**: Check OpenSSL documentation
- **Azure AD configuration**: Contact your Azure administrator
- **Kendra authentication**: Check CloudWatch logs and AWS Support
- **Secrets Manager**: Verify IAM permissions and secret format
