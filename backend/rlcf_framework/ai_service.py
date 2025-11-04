"""
OpenRouter AI Service for RLCF Framework

Provides realistic AI response generation for legal tasks using OpenRouter API.
Replaces dummy placeholder responses with actual AI-generated content for
meaningful evaluation in the RLCF framework.

References:
    RLCF.md Section 3.6 - Dynamic Task Handler System
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AIModelConfig:
    """Configuration for AI model settings."""
    name: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9


class OpenRouterService:
    """
    Service for generating realistic AI responses using OpenRouter API.
    
    Implements AI response generation for legal tasks with configurable models
    and task-specific prompting strategies. Designed to replace placeholder
    responses with meaningful content for RLCF evaluation workflows.
    """
    
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Task-specific system prompts optimized for legal AI
    SYSTEM_PROMPTS = {
        "STATUTORY_RULE_QA": """You are a legal AI assistant specializing in statutory interpretation. 
Provide accurate, well-reasoned answers based on the provided legal context and relevant articles. 
Structure your response with:
1. Direct answer to the question
2. Legal reasoning and analysis
3. References to relevant statutory provisions
4. Confidence level in your assessment""",
        
        "QA": """You are a legal AI assistant. Provide accurate, comprehensive answers 
to legal questions based on the provided context. Include relevant legal principles, 
precedents, and practical implications.""",
        
        "CLASSIFICATION": """You are a legal document classifier. Analyze the provided text 
and classify it into appropriate legal categories. Explain your classification reasoning 
and provide confidence scores for each category.""",
        
        "SUMMARIZATION": """You are a legal document summarizer. Create concise, accurate 
summaries that capture key legal points, obligations, and implications while maintaining 
legal precision.""",
        
        "PREDICTION": """You are a legal outcome predictor. Analyze the provided facts 
and predict likely legal outcomes based on applicable law, precedents, and legal principles. 
Provide reasoning and confidence levels.""",
        
        "DRAFTING": """You are a legal drafting assistant. Create or revise legal documents 
with attention to legal precision, completeness, and compliance with applicable standards.""",
        
        "RISK_SPOTTING": """You are a legal risk assessment specialist. Identify potential 
legal risks, compliance issues, and liability concerns in the provided content. 
Categorize risks by severity and likelihood.""",
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _build_prompt(self, task_type: str, input_data: Dict[str, Any]) -> str:
        """
        Build task-specific prompt for AI generation.
        
        Args:
            task_type: Type of legal task (QA, CLASSIFICATION, etc.)
            input_data: Task input data containing question, context, etc.
            
        Returns:
            str: Formatted prompt for AI generation
        """
        if task_type == "STATUTORY_RULE_QA":
            question = input_data.get("question", "")
            context = input_data.get("context_full", "")
            articles = input_data.get("relevant_articles", "")
            
            prompt = f"""Question: {question}

Legal Context: {context}

Relevant Articles: {articles}

Please provide a comprehensive legal answer that:
1. Directly addresses the question
2. Cites relevant legal provisions
3. Explains the legal reasoning
4. Indicates your confidence level (high/medium/low)"""
            
        elif task_type == "QA":
            question = input_data.get("question", "")
            context = input_data.get("context", "")
            
            prompt = f"""Question: {question}

Context: {context}

Please provide a clear, accurate answer with legal reasoning."""
            
        elif task_type == "CLASSIFICATION":
            text = input_data.get("text", "")
            
            prompt = f"""Text to classify: {text}

Please classify this text into appropriate legal categories and explain your reasoning."""
            
        elif task_type == "SUMMARIZATION":
            document = input_data.get("document", "")
            
            prompt = f"""Document to summarize: {document}

Please provide a concise legal summary highlighting key points, obligations, and implications."""
            
        else:
            # Generic prompt for other task types
            prompt = f"Task Type: {task_type}\n\nInput: {json.dumps(input_data, indent=2)}\n\nPlease provide an appropriate response."
        
        return prompt
    
    async def generate_response(
        self, 
        task_type: str, 
        input_data: Dict[str, Any], 
        model_config: AIModelConfig
    ) -> Dict[str, Any]:
        """
        Generate AI response for a legal task using OpenRouter.
        
        Args:
            task_type: Type of legal task (STATUTORY_RULE_QA, QA, etc.)
            input_data: Task input data
            model_config: AI model configuration with API key
            
        Returns:
            Dict[str, Any]: Generated AI response with metadata
            
        Raises:
            Exception: If API request fails or returns invalid response
        """
        try:
            session = await self._get_session()
            
            system_prompt = self.SYSTEM_PROMPTS.get(
                task_type, 
                "You are a helpful legal AI assistant."
            )
            user_prompt = self._build_prompt(task_type, input_data)
            
            payload = {
                "model": model_config.name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": model_config.temperature,
                "max_tokens": model_config.max_tokens,
                "top_p": model_config.top_p,
            }
            
            headers = {
                "Authorization": f"Bearer {model_config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://rlcf-framework.com",  # Replace with your domain
                "X-Title": "RLCF Framework"
            }
            
            logger.info(f"Generating AI response for task_type: {task_type}, model: {model_config.name}")
            
            async with session.post(
                f"{self.OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error {response.status}: {error_text}")
                    raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                
                data = await response.json()
                
                if "choices" not in data or not data["choices"]:
                    logger.error(f"Invalid OpenRouter response: {data}")
                    raise Exception("Invalid response from OpenRouter API")
                
                ai_content = data["choices"][0]["message"]["content"]
                
                # Parse response based on task type
                parsed_response = self._parse_ai_response(task_type, ai_content, input_data)
                
                # Add metadata
                parsed_response.update({
                    "model_name": model_config.name,
                    "generated_at": data.get("created"),
                    "usage": data.get("usage", {}),
                    "raw_content": ai_content
                })
                
                logger.info(f"Successfully generated AI response for task {task_type}")
                return parsed_response
                
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            # Return fallback response to prevent workflow interruption
            return self._get_fallback_response(task_type, str(e))
    
    def _parse_ai_response(self, task_type: str, ai_content: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse AI response into structured format based on task type.
        
        Args:
            task_type: Type of legal task
            ai_content: Raw AI response content
            input_data: Original task input for context
            
        Returns:
            Dict[str, Any]: Structured response data
        """
        base_response = {
            "response_text": ai_content,
            "task_type": task_type,
            "confidence": self._extract_confidence(ai_content)
        }
        
        if task_type == "STATUTORY_RULE_QA":
            return {
                **base_response,
                "answer": ai_content,
                "legal_reasoning": self._extract_reasoning(ai_content),
                "cited_articles": self._extract_citations(ai_content),
                "question": input_data.get("question", "")
            }
        
        elif task_type == "CLASSIFICATION":
            return {
                **base_response,
                "classifications": self._extract_classifications(ai_content),
                "reasoning": self._extract_reasoning(ai_content)
            }
        
        elif task_type == "QA":
            return {
                **base_response,
                "answer": ai_content,
                "reasoning": self._extract_reasoning(ai_content)
            }
        
        else:
            return base_response
    
    def _extract_confidence(self, content: str) -> str:
        """Extract confidence level from AI response."""
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in ["high confidence", "very confident", "certain"]):
            return "high"
        elif any(phrase in content_lower for phrase in ["medium confidence", "moderately confident", "likely"]):
            return "medium"
        elif any(phrase in content_lower for phrase in ["low confidence", "uncertain", "unclear"]):
            return "low"
        else:
            return "medium"  # default
    
    def _extract_reasoning(self, content: str) -> str:
        """Extract reasoning section from AI response."""
        # Simple heuristic - look for reasoning keywords
        lines = content.split('\n')
        reasoning_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ["because", "reasoning", "analysis", "based on", "according to"]):
                reasoning_lines.append(line.strip())
        
        return ' '.join(reasoning_lines) if reasoning_lines else content[:200] + "..."
    
    def _extract_citations(self, content: str) -> list:
        """Extract legal citations from AI response."""
        # Simple pattern matching for legal citations
        citations = []
        lines = content.split('\n')
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ["article", "section", "§", "statute", "code"]):
                citations.append(line.strip())
        
        return citations
    
    def _extract_classifications(self, content: str) -> list:
        """Extract classifications from AI response."""
        # Simple extraction - look for categories or labels
        classifications = []
        lines = content.split('\n')
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ["category", "classification", "type", "class"]):
                classifications.append(line.strip())
        
        return classifications
    
    def _get_fallback_response(self, task_type: str, error_msg: str) -> Dict[str, Any]:
        """
        Generate fallback response when AI generation fails.
        
        Args:
            task_type: Type of legal task
            error_msg: Error message from failed generation
            
        Returns:
            Dict[str, Any]: Fallback response structure
        """
        return {
            "response_text": f"AI response generation failed: {error_msg}. This is a fallback response.",
            "task_type": task_type,
            "confidence": "low",
            "is_fallback": True,
            "error": error_msg,
            "model_name": "fallback",
            "generated_at": None
        }


# Singleton instance for global use
openrouter_service = OpenRouterService()


async def cleanup_ai_service():
    """Cleanup function to close HTTP session."""
    await openrouter_service.close()