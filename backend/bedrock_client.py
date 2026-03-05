"""
Bedrock API client for querying Knowledge Base and generating responses.
"""
import boto3
import logging
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class BedrockClient:
    """Client for interacting with AWS Bedrock Knowledge Base."""

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize Bedrock client.
        
        Args:
            region_name: AWS region where Bedrock is deployed
        """
        self.client = boto3.client(
            "bedrock-agent-runtime",
            region_name=region_name
        )

    def query_knowledge_base(
        self,
        query: str,
        knowledge_base_id: str,
        max_results: int = 5
    ) -> Dict:
        """
        Query Bedrock Knowledge Base with user question.
        
        Args:
            query: User's natural language question
            knowledge_base_id: ID of the Bedrock Knowledge Base
            max_results: Maximum number of source documents to retrieve
        
        Returns:
            Dictionary containing:
                - generated_response: LLM-generated answer
                - retrieved_references: List of source documents with metadata
                - citations: Citation information
        
        Raises:
            ClientError: If Bedrock API call fails
        """
        try:
            logger.info(f"Querying Knowledge Base {knowledge_base_id} with query: {query[:100]}...")
            
            response = self.client.retrieve_and_generate(
                input={
                    "text": query
                },
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": knowledge_base_id,
                        "modelArn": f"arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2",
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {
                                "numberOfResults": max_results,
                                "overrideSearchType": "HYBRID"
                            }
                        }
                    }
                }
            )
            
            logger.info(f"Successfully retrieved response with {len(response.get('citations', []))} citations")
            
            return {
                "generated_response": response.get("output", {}).get("text", ""),
                "retrieved_references": self._extract_references(response),
                "citations": response.get("citations", [])
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            logger.error(f"Bedrock API error: {error_code} - {error_message}")
            
            # Handle specific error types
            if error_code == "ThrottlingException":
                raise Exception("Service is currently busy. Please try again in a moment.")
            elif error_code == "ValidationException":
                raise Exception("Invalid request format. Please check your query.")
            else:
                raise Exception(f"Failed to generate response: {error_message}")

    def _extract_references(self, response: Dict) -> List[Dict]:
        """
        Extract source document references from Bedrock response.
        
        Args:
            response: Raw Bedrock API response
        
        Returns:
            List of reference dictionaries with metadata
        """
        references = []
        
        for citation in response.get("citations", []):
            for reference in citation.get("retrievedReferences", []):
                content = reference.get("content", {}).get("text", "")
                location = reference.get("location", {})
                metadata = reference.get("metadata", {})
                
                # Extract SharePoint-specific metadata
                ref_dict = {
                    "content": content[:500],  # Limit excerpt length
                    "location": location,
                    "metadata": metadata,
                    "score": reference.get("score", 0.0)
                }
                
                references.append(ref_dict)
        
        return references
