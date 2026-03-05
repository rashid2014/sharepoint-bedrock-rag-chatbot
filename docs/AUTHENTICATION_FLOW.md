# Authentication Flow: Kendra with Azure AD Certificate-Based Authentication

## Overview

This document explains how AWS Kendra SharePoint Connector V2.0 authenticates to Microsoft 365 (SharePoint Online) using Azure AD App-Only authentication with certificate-based signature verification.

## Key Components

1. **X.509 Certificate**: Public/private key pair for cryptographic authentication
2. **Azure AD (Entra ID)**: Microsoft's identity platform
3. **AWS Secrets Manager**: Secure storage for private key and certificate
4. **Kendra Connector**: AWS service that handles authentication internally
5. **SharePoint Online**: Document repository

## Does Kendra Use MSAL?

**Answer: No, Kendra does NOT use MSAL (Microsoft Authentication Library) directly.**

Instead, Kendra implements the OAuth 2.0 client credentials flow with JWT bearer token assertion (RFC 7523) natively. Here's how it works:

### What Kendra Does Internally

```typescript
// Conceptual flow (Kendra handles this internally)
class KendraSharePointAuthenticator {
  
  async authenticate() {
    // 1. Retrieve credentials from Secrets Manager
    const credentials = await getSecretsManagerCredentials();
    const { clientId, tenantId, certificate, privateKey } = credentials;
    
    // 2. Create JWT assertion
    const jwt = this.createJWTAssertion({
      clientId,
      tenantId,
      certificate,
      privateKey
    });
    
    // 3. Request access token from Azure AD
    const token = await this.requestAccessToken(jwt, tenantId);
    
    // 4. Use token to access SharePoint
    return token;
  }
  
  createJWTAssertion({ clientId, tenantId, certificate, privateKey }) {
    // Create JWT header
    const header = {
      alg: 'RS256',  // RSA signature with SHA-256
      typ: 'JWT',
      x5t: this.getCertificateThumbprint(certificate)  // Certificate thumbprint
    };
    
    // Create JWT payload
    const payload = {
      aud: `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`,
      iss: clientId,  // Issuer is the client application
      sub: clientId,  // Subject is also the client application
      jti: this.generateUUID(),  // Unique token ID
      nbf: Math.floor(Date.now() / 1000),  // Not before
      exp: Math.floor(Date.now() / 1000) + 600  // Expires in 10 minutes
    };
    
    // Sign JWT with private key
    const signedJWT = this.signWithPrivateKey(header, payload, privateKey);
    
    return signedJWT;
  }
  
  async requestAccessToken(jwt, tenantId) {
    const tokenEndpoint = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
    
    const response = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: clientId,
        client_assertion_type: 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        client_assertion: jwt,  // Signed JWT
        scope: 'https://graph.microsoft.com/.default',
        grant_type: 'client_credentials'
      })
    });
    
    const { access_token } = await response.json();
    return access_token;
  }
}
```

## Detailed Authentication Flow

### Phase 1: Setup (One-Time)

```
┌─────────────────┐
│  Administrator  │
└────────┬────────┘
         │
         │ 1. Generate certificate
         ▼
┌─────────────────┐
│   OpenSSL       │
│  - Private Key  │
│  - Public Cert  │
└────────┬────────┘
         │
         │ 2. Upload public cert
         ▼
┌─────────────────┐
│   Azure AD      │
│  App Registration│
│  - Client ID    │
│  - Tenant ID    │
│  - Certificate  │
└─────────────────┘
         │
         │ 3. Store private key
         ▼
┌─────────────────┐
│ AWS Secrets Mgr │
│  - Private Key  │
│  - Certificate  │
│  - Client ID    │
│  - Tenant ID    │
└─────────────────┘
```

### Phase 2: Runtime Authentication (Every Sync)

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Kendra     │         │   Secrets    │         │   Azure AD   │         │  SharePoint  │
│  Connector   │         │   Manager    │         │  Token EP    │         │   Online     │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │                        │
       │ 1. Get credentials     │                        │                        │
       ├───────────────────────>│                        │                        │
       │                        │                        │                        │
       │ 2. Return credentials  │                        │                        │
       │   (client_id, tenant_id,                        │                        │
       │    certificate, private_key)                    │                        │
       │<───────────────────────┤                        │                        │
       │                        │                        │                        │
       │ 3. Create JWT assertion│                        │                        │
       │    - Header: {alg: RS256, x5t: thumbprint}      │                        │
       │    - Payload: {aud, iss, sub, exp}              │                        │
       │    - Sign with private key                      │                        │
       │                        │                        │                        │
       │ 4. POST to token endpoint                       │                        │
       │    with signed JWT     │                        │                        │
       ├────────────────────────────────────────────────>│                        │
       │                        │                        │                        │
       │                        │    5. Validate JWT     │                        │
       │                        │       - Verify signature with public cert       │
       │                        │       - Check expiration                        │
       │                        │       - Validate claims                         │
       │                        │                        │                        │
       │ 6. Return access token │                        │                        │
       │<────────────────────────────────────────────────┤                        │
       │                        │                        │                        │
       │ 7. Access SharePoint with token                                          │
       ├─────────────────────────────────────────────────────────────────────────>│
       │                        │                        │                        │
       │                        │                        │    8. Validate token   │
       │                        │                        │       with Azure AD    │
       │                        │                        │                        │
       │ 9. Return documents    │                        │                        │
       │<─────────────────────────────────────────────────────────────────────────┤
       │                        │                        │                        │
```

## JWT Structure

### Header
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "x5t": "NjVBRjY5MDlCMUIwNzU4RTA2QzZFMDQ4QzQ2MDAyQjVDNjk1RTM2Qg"
}
```

### Payload
```json
{
  "aud": "https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token",
  "iss": "{client-id}",
  "sub": "{client-id}",
  "jti": "22b3bb26-e046-42df-9c96-65dbd72c1c81",
  "nbf": 1609459200,
  "exp": 1609459800
}
```

### Signature
```
RSASHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  private_key
)
```

## Security Mechanisms

### 1. Asymmetric Cryptography

- **Private Key**: Kept secret in AWS Secrets Manager, used to sign JWT
- **Public Key**: Uploaded to Azure AD, used to verify JWT signature
- **Algorithm**: RS256 (RSA Signature with SHA-256)

### 2. Certificate Thumbprint (x5t)

The JWT header includes the certificate thumbprint (x5t claim):
```typescript
const thumbprint = crypto
  .createHash('sha1')
  .update(certificate)
  .digest('base64url');
```

Azure AD uses this to identify which certificate to use for verification.

### 3. Token Expiration

- **JWT Assertion**: Valid for 10 minutes (600 seconds)
- **Access Token**: Valid for 1 hour (3600 seconds)
- Kendra automatically refreshes tokens before expiration

### 4. Audience Validation

Azure AD validates that the JWT `aud` claim matches the token endpoint:
```
aud: https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token
```

### 5. Issuer/Subject Validation

Azure AD validates that `iss` and `sub` match the registered client ID.

## Why This is More Secure Than Password-Based Auth

| Aspect | Certificate-Based | Password-Based |
|--------|-------------------|----------------|
| **Credential Type** | Asymmetric key pair | Shared secret |
| **Phishing Resistant** | ✅ Yes | ❌ No |
| **MFA Compatible** | ✅ Yes | ❌ No |
| **Rotation** | Easy (upload new cert) | Requires password change |
| **Compromise Impact** | Limited (cert can be revoked) | High (password exposed) |
| **Audit Trail** | Certificate thumbprint logged | Generic login |
| **Expiration** | Built-in (certificate validity) | Manual policy |

## Token Validation by Azure AD

When Kendra sends the signed JWT to Azure AD, the following validation occurs:

```typescript
// Azure AD validation process (conceptual)
async function validateJWT(jwt, clientId) {
  // 1. Decode JWT header to get certificate thumbprint (x5t)
  const { x5t } = decodeJWTHeader(jwt);
  
  // 2. Retrieve public certificate from app registration
  const publicCert = await getPublicCertificate(clientId, x5t);
  
  // 3. Verify JWT signature using public certificate
  const isValid = crypto.verify(
    'RSA-SHA256',
    jwt,
    publicCert
  );
  
  if (!isValid) {
    throw new Error('Invalid signature');
  }
  
  // 4. Validate JWT claims
  const payload = decodeJWTPayload(jwt);
  
  if (payload.exp < Date.now() / 1000) {
    throw new Error('Token expired');
  }
  
  if (payload.iss !== clientId || payload.sub !== clientId) {
    throw new Error('Invalid issuer or subject');
  }
  
  if (payload.aud !== `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`) {
    throw new Error('Invalid audience');
  }
  
  // 5. Issue access token
  return generateAccessToken(clientId, scopes);
}
```

## Kendra's Internal Implementation

Kendra SharePoint Connector V2.0 implements this flow using:

1. **AWS SDK for Secrets Manager**: Retrieve credentials
2. **OpenSSL/BoringSSL**: Cryptographic operations (signing, hashing)
3. **HTTP Client**: POST requests to Azure AD token endpoint
4. **Microsoft Graph API Client**: Access SharePoint with token

**You don't need to implement any of this** - Kendra handles it all internally when you provide:
- Client ID
- Tenant ID
- Certificate (PEM format)
- Private Key (PEM format)

## Comparison: MSAL vs Kendra Native Implementation

### MSAL (Microsoft Authentication Library)

```typescript
// If you were using MSAL (you're NOT)
import { ConfidentialClientApplication } from '@azure/msal-node';

const msalClient = new ConfidentialClientApplication({
  auth: {
    clientId: 'xxx',
    authority: 'https://login.microsoftonline.com/xxx',
    clientCertificate: {
      thumbprint: 'xxx',
      privateKey: 'xxx'
    }
  }
});

const token = await msalClient.acquireTokenByClientCredential({
  scopes: ['https://graph.microsoft.com/.default']
});
```

### Kendra Native (What Actually Happens)

```json
// You just provide this in Secrets Manager
{
  "auth_type": "azure_ad",
  "client_id": "xxx",
  "tenant_id": "xxx",
  "certificate": "-----BEGIN CERTIFICATE-----...",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----..."
}
```

**Kendra does the rest internally** - no MSAL required!

## Troubleshooting Authentication

### Check JWT Signature

```bash
# Decode JWT (without verification)
echo "eyJhbGc..." | base64 -d | jq .

# Verify JWT signature manually
openssl dgst -sha256 -verify public-key.pem -signature signature.bin data.bin
```

### Test Certificate

```bash
# Verify certificate is valid
openssl x509 -in certificate.pem -text -noout

# Check certificate expiration
openssl x509 -in certificate.pem -noout -enddate

# Verify private key matches certificate
openssl x509 -in certificate.pem -noout -modulus | openssl md5
openssl rsa -in private-key.pem -noout -modulus | openssl md5
# These should match
```

### Monitor Authentication

```bash
# Watch Kendra logs for authentication events
aws logs tail /aws/kendra/sharepoint-genai-index --follow --filter-pattern "authentication"
```

## Summary

**Key Takeaways:**

1. ✅ Kendra natively supports Azure AD certificate-based authentication
2. ✅ No MSAL library needed - Kendra implements OAuth 2.0 JWT bearer flow internally
3. ✅ You only provide: client ID, tenant ID, certificate, and private key
4. ✅ Kendra handles: JWT creation, signing, token requests, and token refresh
5. ✅ Azure AD validates: signature, expiration, issuer, subject, and audience
6. ✅ Most secure authentication method for production environments

**You don't need to write any authentication code** - just configure the credentials and Kendra does everything!
