"""
AWS Lambda function for SharePoint Bedrock RAG Chatbot.

Handles query requests from API Gateway, orchestrates Bedrock Knowledge Base
queries, and returns formatted responses with source attribution.
"""
import json
import logging
import os
import uuid
from typing import Dict, Any
from datetime import datetime

from bedrock_client import BedrockClient
from utils import (
    format_response,
    handle_error,
    create_success_response,
    validate_query
)

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(getattr(logging, log_level))

# Initialize Bedrock client
REGION = os.environ.get("AWS_REGION", "us-east-1")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")

bedrock_client = BedrockClient(region_name=REGION)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for query processing.
    
    Args:
        event: API Gateway proxy event with query in body
        context: Lambda context object
    
    Returns:
        API Gateway proxy response with LLM answer and sources
    """
    start_time = datetime.utcnow()
    session_id = str(uuid.uuid4())
    
    try:
        # Handle OPTIONS request for CORS
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                },
                "body": ""
            }
        
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "").strip()
        session_id = body.get("session_id", session_id)
        max_tokens = body.get("max_tokens", 512)
        
        # Validate inputs
        if not KNOWLEDGE_BASE_ID:
            raise ValueError("KNOWLEDGE_BASE_ID environment variable not set")
        
        validate_query(query)
        
        # Log request
        logger.info(
            "Processing query",
            extra={
                "session_id": session_id,
                "query_length": len(query),
                "max_tokens": max_tokens,
                "timestamp": start_time.isoformat()
            }
        )
        
        # Query Bedrock Knowledge Base
        bedrock_response = bedrock_client.query_knowledge_base(
            query=query,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            max_results=5
        )
        
        # Check if any results were found
        if not bedrock_response.get("retrieved_references"):
            raise Exception("No relevant documents found for your query")
        
        # Format response
        formatted_response = format_response(bedrock_response, session_id)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        formatted_response["processing_time_ms"] = int(processing_time)
        
        # Log successful response
        logger.info(
            "Query processed successfully",
            extra={
                "session_id": session_id,
                "sources_count": len(formatted_response.get("sources", [])),
                "processing_time_ms": processing_time,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return create_success_response(formatted_response)
        
    except ValueError as e:
        # Validation errors
        logger.warning(f"Validation error: {str(e)}")
        return handle_error(e, query=body.get("query", ""), session_id=session_id)
        
    except Exception as e:
        # All other errors
        return handle_error(e, query=body.get("query", ""), session_id=session_id)
