"""
Utility functions for Lambda handler.
"""
import json
import logging
import traceback
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger()


def format_response(bedrock_response: Dict, session_id: str) -> Dict:
    """
    Format Bedrock response for frontend consumption.
    
    Args:
        bedrock_response: Raw response from Bedrock API
        session_id: Session identifier
    
    Returns:
        Formatted response with sources
    """
    generated_text = bedrock_response.get("generated_response", "")
    references = bedrock_response.get("retrieved_references", [])
    
    # Format source documents
    sources = []
    for ref in references:
        location = ref.get("location", {})
        metadata = ref.get("metadata", {})
        
        # Extract SharePoint URL and metadata
        source_uri = location.get("s3Location", {}).get("uri", "") or metadata.get("_source_uri", "")
        
        source = {
            "title": metadata.get("_document_title", "Untitled Document"),
            "url": source_uri,
            "excerpt": ref.get("content", "")[:200],  # First 200 chars
            "location": metadata.get("SharePointFileType", "Unknown"),
            "score": ref.get("score", 0.0)
        }
        sources.append(source)
    
    return {
        "response": generated_text,
        "sources": sources,
        "session_id": session_id
    }


def handle_error(error: Exception, query: str = "", session_id: str = "") -> Dict:
    """
    Convert exceptions to user-friendly error messages.
    
    Args:
        error: Exception object
        query: User query (for logging)
        session_id: Session ID (for logging)
    
    Returns:
        API Gateway response with error message
    """
    error_message = str(error)
    error_type = type(error).__name__
    
    # Log error with context
    logger.error(
        "Query processing failed",
        extra={
            "error_type": error_type,
            "error_message": error_message,
            "query": query[:100] if query else "",
            "session_id": session_id,
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Determine user-friendly message
    if "throttl" in error_message.lower():
        user_message = "The service is currently busy. Please try again in a moment."
        status_code = 503
    elif "timeout" in error_message.lower():
        user_message = "The request took too long to process. Please try again."
        status_code = 504
    elif "validation" in error_message.lower():
        user_message = "Invalid request format. Please check your query."
        status_code = 400
    elif "no relevant documents" in error_message.lower():
        user_message = "I couldn't find any relevant documents to answer your question. Please try rephrasing or ask about different content."
        status_code = 200  # Not an error, just no results
    else:
        user_message = "I'm having trouble generating a response right now. Please try again in a moment."
        status_code = 500
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps({
            "error": user_message,
            "error_type": error_type,
            "session_id": session_id
        })
    }


def create_success_response(data: Dict) -> Dict:
    """
    Create successful API Gateway response.
    
    Args:
        data: Response data dictionary
    
    Returns:
        API Gateway response format
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(data)
    }


def validate_query(query: str) -> None:
    """
    Validate user query input.
    
    Args:
        query: User's query string
    
    Raises:
        ValueError: If query is invalid
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    if len(query) > 1000:
        raise ValueError("Query exceeds maximum length of 1000 characters")
    
    # Check for potential injection attempts
    dangerous_patterns = ['<script', 'javascript:', 'onerror=']
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            raise ValueError("Invalid characters in query")
