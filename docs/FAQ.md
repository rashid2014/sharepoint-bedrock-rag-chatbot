# Frequently Asked Questions (FAQ)

## Authentication

### Q: Does Kendra use MSAL (Microsoft Authentication Library)?

**A: No.** Kendra SharePoint Connector V2.0 implements the OAuth 2.0 client credentials flow with JWT bearer token assertion natively. You don't need to install or configure MSAL. Kendra handles all authentication internally when you provide the certificate and private key in AWS Secrets Manager.

See: [Authentication Flow Documentation](AUTHENTICATION_FLOW.md)

### Q: How does certificate-based authentication work?

**A:** The flow is:
1. You generate an X.509 certificate (public/private key pair)
2. Upload the public certificate to Azure AD
3. Store the private key in AWS Secrets Manager
4. Kendra creates a JWT, signs it with the private key
5. Azure AD validates the signature using the uploaded public certificate
6. Azure AD issues an access token
7. Kendra uses the token to access SharePoint

See: [Azure AD Certificate Authentication Guide](AZURE_AD_CERTIFICATE_AUTH.md)

### Q: Which authentication method should I use?

**A: Azure AD App-Only (certificate-based)** for production. It's the most secure method:
- ✅ Passwordless
- ✅ MFA compatible
- ✅ Phishing resistant
- ✅ Easy rotation
- ✅ Audit trail

Other methods (OAuth 2.0, Basic) are suitable for development/testing only.

### Q: How often do I need to rotate certificates?

**A:** Recommended rotation schedule:
- **Development**: 1 year
- **Production**: 6-12 months
- **High Security**: 3-6 months

Set up CloudWatch alarms to notify you 30 days before expiration.

### Q: Can I use the same certificate for multiple environments?

**A:** Not recommended. Use separate certificates for:
- Development
- Staging
- Production

This limits the blast radius if a certificate is compromised.

## Kendra and SharePoint

### Q: Does Kendra copy files from SharePoint to S3?

**A: No.** Kendra indexes documents directly from SharePoint Online. Files remain in SharePoint. Only metadata and text content are indexed in Kendra.

### Q: What file types does Kendra support?

**A:** Kendra supports:
- Documents: PDF, DOCX, XLSX, PPTX, TXT, RTF
- Web: HTML, XML
- Images: Text extraction from images (OCR)
- OneNote: Notebooks (requires additional permissions)

### Q: How long does initial sync take?

**A:** Depends on document count:
- 1,000 documents: ~30 minutes
- 10,000 documents: ~2-3 hours
- 100,000 documents: ~8-12 hours

Subsequent syncs are incremental and much faster.

### Q: Can I index multiple SharePoint sites?

**A:** Yes, but you need to:
1. List all site URLs in the `sharepointFolders` configuration
2. Ensure the Azure AD app has permissions to all sites
3. Consider using `Sites.Selected` permission for granular control

### Q: Does Kendra support SharePoint permissions (ACL)?

**A: Yes.** Enable ACL in the configuration:
```bash
cdk deploy -c enable_acl=true
```

**Note**: ACL requires additional API permissions and only works with certain sync modes.

## Bedrock and RAG

### Q: Which Bedrock models are supported?

**A:** The solution uses:
- **Embedding**: Amazon Titan Embed Text v1
- **LLM**: Anthropic Claude v2 (configurable)

You can modify the model in `bedrock-stack.ts`.

### Q: How many documents does Bedrock retrieve per query?

**A:** Default is 5 documents (top-k=5). You can adjust this in `bedrock_client.py`:
```python
max_results=5  # Change to 3-10 based on your needs
```

### Q: Can I customize the LLM prompt?

**A: Yes.** Modify the `retrieve_and_generate` call in `backend/bedrock_client.py` to include custom prompts or instructions.

### Q: How much does this cost?

**A:** Approximate monthly costs (us-east-1):
- Kendra Enterprise: $810/month (primary cost)
- Bedrock (1M tokens): $8-24/month
- Lambda: $0.20/month
- API Gateway: $0.35/month
- Other services: ~$3/month

**Total**: ~$820-840/month

For testing, use Kendra Developer Edition ($1.40/hour when active).

## Deployment

### Q: Can I deploy to multiple AWS regions?

**A: Yes**, but Bedrock availability varies by region. Supported regions:
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- eu-west-1 (Ireland)
- ap-southeast-1 (Singapore)

Check [AWS Bedrock regions](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-regions.html) for updates.

### Q: How do I update the infrastructure?

**A:**
```bash
cd infrastructure
npm run build
cdk deploy --all
```

CDK will show you a diff of changes before applying.

### Q: Can I use CloudFormation instead of CDK?

**A:** Yes. Generate CloudFormation templates:
```bash
cdk synth > template.yaml
```

Then deploy using CloudFormation console or CLI.

### Q: How do I rollback a deployment?

**A:**
```bash
# Rollback to previous version
cdk deploy --rollback

# Or destroy and redeploy
cdk destroy --all
cdk deploy --all
```

**Warning**: Destroying Kendra index deletes all indexed data.

## Frontend

### Q: Can I customize the frontend UI?

**A: Yes.** The React frontend is fully customizable:
- Modify components in `frontend/src/components/`
- Update styles in `frontend/src/styles/chat.css`
- Add features like conversation history, user authentication, etc.

### Q: Can I deploy the frontend to AWS?

**A: Yes.** Options:
1. **S3 + CloudFront**: Static hosting with CDN
2. **Amplify**: Managed hosting with CI/CD
3. **ECS/Fargate**: Containerized deployment
4. **Lambda@Edge**: Serverless SSR

See [Deployment Guide](DEPLOYMENT.md) for details.

### Q: How do I enable user authentication in the frontend?

**A:** Add Amazon Cognito:
1. Create Cognito User Pool
2. Configure API Gateway authorizer
3. Add Cognito authentication to React app
4. Pass user token to Lambda for ACL

## Security

### Q: Is my private key secure?

**A: Yes**, if you follow best practices:
- ✅ Store only in AWS Secrets Manager (encrypted with KMS)
- ✅ Delete local copies after upload
- ✅ Use IAM policies to restrict access
- ✅ Enable CloudTrail logging for secret access
- ✅ Rotate certificates regularly

### Q: Can I use AWS KMS for certificate encryption?

**A: Yes.** Secrets Manager automatically encrypts secrets with KMS. You can use a custom KMS key:
```typescript
const kmsKey = new kms.Key(this, 'SecretsKey', {
  enableKeyRotation: true
});

const secret = new secretsmanager.Secret(this, 'Secret', {
  encryptionKey: kmsKey
});
```

### Q: How do I audit access to SharePoint documents?

**A:** Enable:
1. **CloudTrail**: Logs all AWS API calls
2. **CloudWatch Logs**: Logs Kendra sync jobs
3. **SharePoint Audit Logs**: Logs document access
4. **Bedrock Logging**: Logs LLM queries

### Q: Is data encrypted in transit?

**A: Yes.** All connections use TLS 1.2+:
- Frontend ↔ API Gateway: HTTPS
- Lambda ↔ Bedrock: TLS
- Lambda ↔ Kendra: TLS
- Kendra ↔ SharePoint: HTTPS

## Troubleshooting

### Q: Sync job fails with "Authentication failed"

**A:** Check:
1. Certificate hasn't expired: `openssl x509 -in cert.pem -noout -enddate`
2. Client ID and Tenant ID are correct
3. Certificate was uploaded to Azure AD
4. Admin consent was granted

### Q: "Insufficient permissions" error

**A:** Ensure:
1. API permissions are granted in Azure AD
2. Admin consent is provided
3. Wait 5-10 minutes for permissions to propagate
4. Check required permissions match your auth type

### Q: Frontend can't connect to API

**A:** Verify:
1. API endpoint URL in `.env` is correct
2. CORS is configured in API Gateway
3. API Gateway is deployed to `prod` stage
4. Test with curl: `curl -X POST <api-endpoint> -d '{"query":"test"}'`

### Q: Lambda timeout errors

**A:** Solutions:
1. Increase Lambda timeout (max 15 minutes)
2. Reduce number of retrieved documents
3. Use streaming responses for large queries
4. Check Bedrock service availability

### Q: High costs

**A:** Optimize:
1. Use Kendra Developer Edition for testing
2. Reduce sync frequency
3. Use inclusion/exclusion filters to index fewer documents
4. Monitor Bedrock token usage
5. Set up billing alerts

## Performance

### Q: How fast are query responses?

**A:** Typical latency:
- Kendra retrieval: 1-2 seconds
- Bedrock generation: 2-5 seconds
- **Total**: 3-7 seconds

Optimize by:
- Reducing retrieved documents (top-k)
- Using faster LLM models
- Implementing caching

### Q: Can I cache responses?

**A: Yes.** Add caching layer:
1. **ElastiCache**: Cache frequent queries
2. **DynamoDB**: Store query history
3. **CloudFront**: Cache API responses (with short TTL)

### Q: How do I scale for high traffic?

**A:** The architecture auto-scales:
- Lambda: Concurrent executions (default 1000)
- API Gateway: Handles millions of requests
- Kendra: Enterprise edition supports high query volume
- Bedrock: Managed service with auto-scaling

Increase Lambda concurrency if needed:
```bash
aws lambda put-function-concurrency \
  --function-name sharepoint-chatbot-query-processor \
  --reserved-concurrent-executions 500
```

## Development

### Q: How do I run tests?

**A:**
```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm test

# Infrastructure tests
cd infrastructure
npm test
```

### Q: Can I use Python for CDK instead of TypeScript?

**A:** The project was converted from Python to TypeScript for better type safety. You can convert back by:
1. Translating TypeScript stacks to Python
2. Updating `cdk.json` to use Python entry point
3. Installing Python CDK dependencies

### Q: How do I add custom Lambda layers?

**A:** In `api-stack.ts`:
```typescript
const layer = new lambda.LayerVersion(this, 'CustomLayer', {
  code: lambda.Code.fromAsset('layers/my-layer'),
  compatibleRuntimes: [lambda.Runtime.PYTHON_3_11]
});

const lambdaFunction = new lambda.Function(this, 'Function', {
  // ... other config
  layers: [layer]
});
```

## Support

### Q: Where can I get help?

**A:**
- **Documentation**: Check `docs/` folder
- **AWS Support**: For Kendra/Bedrock issues
- **Azure Support**: For Azure AD issues
- **GitHub Issues**: For project-specific issues
- **CloudWatch Logs**: For debugging

### Q: How do I report a bug?

**A:**
1. Check CloudWatch logs for error details
2. Verify configuration is correct
3. Try with minimal test case
4. Open GitHub issue with:
   - Error message
   - Steps to reproduce
   - CloudWatch log excerpts (redact sensitive info)
   - CDK/package versions

### Q: Can I contribute to the project?

**A: Yes!** Contributions welcome:
- Bug fixes
- Feature enhancements
- Documentation improvements
- Test coverage
- Performance optimizations

Follow standard GitHub workflow (fork, branch, PR).
