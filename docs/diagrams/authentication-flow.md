# Authentication Flow Diagrams

## Simple Authentication Flow

```mermaid
sequenceDiagram
    participant K as Kendra Connector
    participant S as AWS Secrets Manager
    participant E as Entra ID
    participant SP as SharePoint Online

    K->>S: 1. Get credentials
    S->>K: 2. Return cert + private key
    K->>K: 3. Generate JWT<br/>Sign with private key
    K->>E: 4. POST signed JWT
    E->>E: 5. Validate signature<br/>with public cert
    E->>K: 6. Return access token
    K->>SP: 7. Access SharePoint<br/>with token
    SP->>K: 8. Return documents
```

## Detailed Authentication Flow with Components

```mermaid
sequenceDiagram
    autonumber
    participant K as 🔧 Kendra<br/>Connector
    participant SM as 🔐 Secrets<br/>Manager
    participant E as 🏢 Entra ID<br/>Token Endpoint
    participant SP as 📁 SharePoint<br/>Online

    rect rgb(240, 248, 255)
        Note over K,SM: Phase 1: Credential Retrieval
        K->>SM: GetSecretValue<br/>(sharepoint-chatbot/credentials)
        SM->>K: Return credentials:<br/>• client_id<br/>• tenant_id<br/>• certificate (PEM)<br/>• private_key (PEM)
    end

    rect rgb(255, 250, 240)
        Note over K: Phase 2: JWT Creation & Signing
        K->>K: Create JWT Header:<br/>{"alg":"RS256","typ":"JWT","x5t":"..."}
        K->>K: Create JWT Payload:<br/>{"aud":"...","iss":"client_id",<br/>"sub":"client_id","exp":"..."}
        K->>K: Sign JWT with RSA-SHA256<br/>using private key
    end

    rect rgb(240, 255, 240)
        Note over K,E: Phase 3: Token Request
        K->>E: POST /oauth2/v2.0/token<br/>grant_type=client_credentials<br/>client_assertion=<signed_jwt><br/>scope=https://graph.microsoft.com/.default
        E->>E: Decode JWT header<br/>Extract x5t (cert thumbprint)
        E->>E: Retrieve public certificate<br/>from app registration
        E->>E: Verify JWT signature<br/>using public certificate
        E->>E: Validate claims:<br/>• Expiration (exp)<br/>• Issuer (iss)<br/>• Subject (sub)<br/>• Audience (aud)
        E->>K: Return access_token<br/>(valid for 1 hour)
    end

    rect rgb(255, 240, 245)
        Note over K,SP: Phase 4: SharePoint Access
        K->>SP: GET /sites/.../documents<br/>Authorization: Bearer <access_token>
        SP->>E: Validate token with Entra ID
        E->>SP: Token valid ✓
        SP->>K: Return documents & metadata
    end

    rect rgb(245, 245, 245)
        Note over K: Phase 5: Indexing
        K->>K: Extract text & metadata<br/>Chunk documents<br/>Create search index
    end
```

## Setup Flow (One-Time Configuration)

```mermaid
flowchart TB
    Start([Administrator]) --> Gen[Generate Certificate<br/>openssl genrsa]
    Gen --> Cert[Create X.509 Certificate<br/>Public + Private Key]
    
    Cert --> Azure[Upload to Azure AD]
    Cert --> AWS[Store in AWS Secrets Manager]
    
    Azure --> AppReg[App Registration]
    AppReg --> ClientID[Copy Client ID]
    AppReg --> TenantID[Copy Tenant ID]
    AppReg --> Upload[Upload Public Certificate]
    AppReg --> Perms[Grant API Permissions<br/>Sites.Read.All]
    AppReg --> Consent[Admin Consent]
    
    AWS --> Secret[Create Secret]
    Secret --> Store[Store:<br/>• client_id<br/>• tenant_id<br/>• certificate<br/>• private_key]
    
    Consent --> Deploy[Deploy CDK Stack]
    Store --> Deploy
    
    Deploy --> Kendra[Kendra Index Created]
    Kendra --> Sync[Trigger Initial Sync]
    Sync --> Done([✓ Ready to Use])
    
    style Start fill:#e1f5ff
    style Done fill:#d4edda
    style Azure fill:#fff4e1
    style AWS fill:#ffe1e1
    style Deploy fill:#e1ffe1
```

## JWT Structure and Signing

```mermaid
flowchart LR
    subgraph JWT["JWT Token Structure"]
        Header["Header<br/>{<br/>  alg: 'RS256',<br/>  typ: 'JWT',<br/>  x5t: 'thumbprint'<br/>}"]
        Payload["Payload<br/>{<br/>  aud: 'token_endpoint',<br/>  iss: 'client_id',<br/>  sub: 'client_id',<br/>  exp: timestamp<br/>}"]
        Signature["Signature<br/>RSASHA256(<br/>  header.payload,<br/>  private_key<br/>)"]
    end
    
    Header --> Encode1[Base64URL Encode]
    Payload --> Encode2[Base64URL Encode]
    
    Encode1 --> Concat[Concatenate with '.']
    Encode2 --> Concat
    
    Concat --> Sign[Sign with<br/>Private Key]
    PrivKey[🔑 Private Key<br/>RSA 2048/4096 bit] --> Sign
    
    Sign --> Final[Final JWT:<br/>header.payload.signature]
    
    Final --> Send[Send to Entra ID]
    
    subgraph Validation["Entra ID Validation"]
        Send --> Decode[Decode JWT]
        Decode --> GetCert[Get Public Certificate<br/>using x5t thumbprint]
        PubCert[📜 Public Certificate<br/>Uploaded in Azure AD] --> GetCert
        GetCert --> Verify[Verify Signature]
        Verify --> Check{Valid?}
        Check -->|Yes| Token[Issue Access Token]
        Check -->|No| Reject[Reject Request]
    end
    
    style PrivKey fill:#ffe1e1
    style PubCert fill:#e1ffe1
    style Token fill:#d4edda
    style Reject fill:#f8d7da
```

## Security Flow

```mermaid
flowchart TB
    subgraph Setup["🔧 Setup Phase"]
        A1[Generate Certificate Pair]
        A2[Public Certificate → Azure AD]
        A3[Private Key → AWS Secrets Manager]
        A1 --> A2
        A1 --> A3
    end
    
    subgraph Runtime["⚡ Runtime Phase"]
        B1[Kendra Retrieves Private Key]
        B2[Signs JWT with Private Key]
        B3[Sends Signed JWT to Entra ID]
        B1 --> B2 --> B3
    end
    
    subgraph Validation["✓ Validation Phase"]
        C1[Entra ID Retrieves Public Certificate]
        C2[Validates JWT Signature]
        C3{Signature Valid?}
        C4[Issues Access Token]
        C5[Rejects Request]
        C1 --> C2 --> C3
        C3 -->|Yes| C4
        C3 -->|No| C5
    end
    
    subgraph Access["📁 Access Phase"]
        D1[Kendra Uses Token]
        D2[Accesses SharePoint]
        D3[Indexes Documents]
        D1 --> D2 --> D3
    end
    
    Setup --> Runtime
    Runtime --> Validation
    Validation --> Access
    
    style A2 fill:#fff4e1
    style A3 fill:#ffe1e1
    style C4 fill:#d4edda
    style C5 fill:#f8d7da
    style D3 fill:#e1f5ff
```

## Component Interaction Overview

```mermaid
graph TB
    subgraph AWS["☁️ AWS Cloud"]
        SM[Secrets Manager<br/>🔐<br/>Stores Private Key]
        Kendra[Kendra Connector<br/>🔧<br/>Handles Auth]
        Index[Kendra Index<br/>📊<br/>Stores Metadata]
    end
    
    subgraph Azure["☁️ Microsoft Azure"]
        EntraID[Entra ID<br/>🏢<br/>Token Endpoint]
        AppReg[App Registration<br/>📋<br/>Stores Public Cert]
        SP[SharePoint Online<br/>📁<br/>Document Store]
    end
    
    SM -->|1. Get Credentials| Kendra
    Kendra -->|2. Create & Sign JWT| Kendra
    Kendra -->|3. Request Token| EntraID
    AppReg -.->|Public Cert| EntraID
    EntraID -->|4. Validate & Issue Token| Kendra
    Kendra -->|5. Access with Token| SP
    SP -->|6. Return Documents| Kendra
    Kendra -->|7. Index Content| Index
    
    style SM fill:#ffe1e1
    style AppReg fill:#fff4e1
    style EntraID fill:#e1ffe1
    style SP fill:#e1f5ff
    style Index fill:#f0e1ff
```

## Token Lifecycle

```mermaid
stateDiagram-v2
    [*] --> CredentialRetrieval: Sync Job Starts
    
    CredentialRetrieval --> JWTCreation: Got Credentials
    JWTCreation --> JWTSigning: JWT Created
    JWTSigning --> TokenRequest: JWT Signed
    
    TokenRequest --> TokenValidation: Sent to Entra ID
    TokenValidation --> TokenIssued: Signature Valid
    TokenValidation --> AuthFailed: Signature Invalid
    
    TokenIssued --> SharePointAccess: Token Received
    SharePointAccess --> DocumentRetrieval: Authorized
    DocumentRetrieval --> Indexing: Documents Retrieved
    
    Indexing --> TokenExpired: After 1 hour
    TokenExpired --> TokenRefresh: Need New Token
    TokenRefresh --> JWTCreation: Create New JWT
    
    Indexing --> [*]: Sync Complete
    AuthFailed --> [*]: Sync Failed
    
    note right of JWTSigning
        Signs with Private Key
        Algorithm: RS256
    end note
    
    note right of TokenValidation
        Validates with Public Cert
        Checks: exp, iss, sub, aud
    end note
    
    note right of TokenIssued
        Access Token valid for 1 hour
        Refresh before expiration
    end note
```

## Error Handling Flow

```mermaid
flowchart TD
    Start([Kendra Sync Job]) --> GetCreds[Get Credentials<br/>from Secrets Manager]
    
    GetCreds -->|Success| CreateJWT[Create JWT]
    GetCreds -->|Fail| E1[❌ Secrets Access Error]
    
    CreateJWT --> SignJWT[Sign with Private Key]
    SignJWT -->|Success| SendToken[Send to Entra ID]
    SignJWT -->|Fail| E2[❌ Signing Error<br/>Invalid Private Key]
    
    SendToken --> Validate{Validation}
    
    Validate -->|Signature Valid| CheckClaims{Check Claims}
    Validate -->|Signature Invalid| E3[❌ Invalid Signature<br/>Cert Mismatch]
    
    CheckClaims -->|Valid| IssueToken[Issue Access Token]
    CheckClaims -->|Expired| E4[❌ Token Expired]
    CheckClaims -->|Invalid Issuer| E5[❌ Invalid Client ID]
    CheckClaims -->|Invalid Audience| E6[❌ Wrong Audience]
    
    IssueToken --> AccessSP[Access SharePoint]
    
    AccessSP -->|Success| Index[Index Documents]
    AccessSP -->|Fail| E7[❌ SharePoint Access Denied<br/>Check Permissions]
    
    Index --> Success([✓ Sync Complete])
    
    E1 --> Retry{Retry?}
    E2 --> Retry
    E3 --> Retry
    E4 --> Retry
    E5 --> Manual[Manual Intervention Required]
    E6 --> Manual
    E7 --> Retry
    
    Retry -->|Yes<br/>Attempt < 3| GetCreds
    Retry -->|No| Failed([❌ Sync Failed])
    Manual --> Failed
    
    style Success fill:#d4edda
    style Failed fill:#f8d7da
    style E1 fill:#fff3cd
    style E2 fill:#fff3cd
    style E3 fill:#fff3cd
    style E4 fill:#fff3cd
    style E5 fill:#f8d7da
    style E6 fill:#f8d7da
    style E7 fill:#fff3cd
```

---

## How to View These Diagrams

### GitHub
These Mermaid diagrams render automatically on GitHub. Just view this file in your repository.

### VS Code
Install the "Markdown Preview Mermaid Support" extension.

### Online Viewers
- [Mermaid Live Editor](https://mermaid.live/)
- [GitHub Gist](https://gist.github.com/) (supports Mermaid)

### Export as Images
Use the Mermaid CLI to export as PNG/SVG:

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Export diagram
mmdc -i authentication-flow.md -o authentication-flow.png
```

### Embed in Documentation
Most documentation tools support Mermaid:
- GitBook
- Docusaurus
- MkDocs (with plugin)
- Confluence (with plugin)
- Notion (with embed)
