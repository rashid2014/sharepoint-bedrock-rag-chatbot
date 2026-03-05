#!/usr/bin/env node
/**
 * AWS CDK application entry point for SharePoint Bedrock RAG Chatbot.
 * 
 * This application provisions all required AWS resources including:
 * - AWS Secrets Manager for SharePoint credentials
 * - AWS Kendra GenAI Index with SharePoint Connector V2.0
 * - AWS Bedrock Knowledge Base
 * - AWS Lambda function for query processing
 * - AWS API Gateway for frontend integration
 */
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SharePointChatbotStack } from '../lib/stacks/sharepoint-chatbot-stack';

const app = new cdk.App();

// Get configuration from context or environment variables
const sharepointSiteUrl = app.node.tryGetContext('sharepoint_site_url') || 
  process.env.SHAREPOINT_SITE_URL || 
  'https://contoso.sharepoint.com/sites/mysite';

const sharepointFolders = app.node.tryGetContext('sharepoint_folders') || [
  'Shared Documents',
  'Documents'
];

const authType = app.node.tryGetContext('auth_type') || 
  process.env.AUTH_TYPE || 
  'oauth2';

const syncSchedule = app.node.tryGetContext('sync_schedule') || 
  'cron(0 2 * * ? *)';

const enableAcl = app.node.tryGetContext('enable_acl') || false;

// Get AWS account and region from environment
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

// Create environment configuration
const env: cdk.Environment = {
  account,
  region
};

// Create main stack
new SharePointChatbotStack(app, 'SharePointBedrockChatbot', {
  sharepointSiteUrl,
  sharepointFolders,
  authType,
  syncSchedule,
  enableAcl,
  env,
  description: 'SharePoint Bedrock RAG Chatbot - Complete infrastructure stack'
});

app.synth();
