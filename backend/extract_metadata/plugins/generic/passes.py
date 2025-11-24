from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletionMessageParam

from extract_metadata.core.llm_passes import BaseLLMPass, LLMPassPipeline
from extract_metadata.core.parsing import JSONCleaner
from extract_metadata.core.logging import get_logger

logger = get_logger(__name__)

# Placeholder Pydantic schema for generic metadata extraction
class GenericMetadataSchema(BaseModel):
    summary: Optional[str] = Field(None, description="A brief summary of the document.")
    keywords: List[str] = Field(default_factory=list, description="Keywords describing the document content.")

def get_generic_system_prompt(language: str) -> str:
    """
    Returns a generic system prompt for basic metadata extraction.
    """
    return f"""You are an expert at extracting general metadata from various types of documents.
    Your task is to identify and extract key metadata fields from the provided document content.
    Focus on providing a concise summary and relevant keywords.
    The document is in {language}. Ensure the output is valid JSON and adheres to the GenericMetadataSchema."""

class GenericLLMPass(BaseLLMPass):
    """
    A generic LLM pass for basic metadata extraction.
    """
    def __init__(self, json_cleaner: JSONCleaner):
        super().__init__(
            name="GenericLLMPass",
            output_schema=GenericMetadataSchema,
            json_cleaner=json_cleaner
        )

    def get_messages(self, input_content: str, document_context: Dict[str, Any], **kwargs) -> List[ChatCompletionMessageParam]:
        language = document_context.get("language", "en")
        system_prompt = get_generic_system_prompt(language)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content}
        ]

def get_generic_llm_pipeline(reference_extractor_name: Optional[str] = None) -> LLMPassPipeline:
    """
    Factory function to create a generic LLM pipeline.
    """
    json_cleaner = JSONCleaner(reference_extractor_name=reference_extractor_name)
    generic_pass = GenericLLMPass(json_cleaner=json_cleaner)
    return LLMPassPipeline(passes=[generic_pass])
