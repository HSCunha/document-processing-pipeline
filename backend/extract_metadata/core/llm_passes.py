import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, Optional
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam

from extract_metadata.core.model_client import BaseModelClient
from extract_metadata.core.config import OpenAIConfig
from extract_metadata.core.logging import get_logger
from extract_metadata.core.parsing import JSONParser, JSONCleaner

logger = get_logger(__name__)

class BaseLLMPass(ABC):
    """
    Abstract base class for a single LLM interaction pass.
    """
    def __init__(self, name: str, output_schema: Type[BaseModel], json_cleaner: JSONCleaner):
        self.name = name
        self.output_schema = output_schema
        self.json_cleaner = json_cleaner

    @abstractmethod
    def get_messages(self, input_content: str, document_context: Dict[str, Any], **kwargs) -> List[ChatCompletionMessageParam]:
        """
        Prepares the list of messages for the LLM call.

        Args:
            input_content (str): The primary content to be sent to the LLM (e.g., markdown for first pass,
                                 stringified JSON for subsequent passes).
            document_context (Dict[str, Any]): The document object or relevant parts,
                                                including language, initial metadata, etc.
            **kwargs: Additional parameters.

        Returns:
            List[ChatCompletionMessageParam]: List of messages for the LLM.
        """
        pass

    def run_pass(self,
                 model_client: BaseModelClient,
                 model_config: OpenAIConfig, # Pass the specific OpenAIConfig for this pass
                 input_content: str,
                 document_context: Dict[str, Any],
                 temperature: float = 0.0,
                 max_tokens: int = 16384,
                 **kwargs) -> Dict[str, Any]:
        """
        Executes a single LLM pass, including message preparation, API call, and response parsing.

        Args:
            model_client (BaseModelClient): The LLM client to use.
            model_config (OpenAIConfig): The specific OpenAIConfig for this LLM call (e.g., SLM or LLM).
            input_content (str): The primary content for this pass.
            document_context (Dict[str, Any]): The full document context.
            temperature (float): LLM generation temperature.
            max_tokens (int): Max tokens for LLM generation.
            **kwargs: Additional parameters.

        Returns:
            Dict[str, Any]: The cleaned and validated output from the LLM.

        Raises:
            ValueError: If parsing or validation fails.
        """
        messages = self.get_messages(input_content, document_context, **kwargs)
        
        # model_config should already be loaded from env before calling this
        if not model_config.model_name or not model_config.endpoint:
            logger.error(f"LLM model for pass '{self.name}' not configured correctly. Model: {model_config.model_name}, Endpoint: {model_config.endpoint}")
            raise ValueError(f"LLM model for pass '{self.name}' not configured correctly.")
            
        logger.info(f"Executing LLM pass '{self.name}' with model: {model_config.model_name}")

        raw_response = model_client.generate(
            messages=messages,
            model_name=model_config.model_name, # Use the model name from the specific model_config
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=self.output_schema,
            **kwargs
        )
        
        parsed_data = JSONParser.parse_and_validate(raw_response, self.output_schema)
        # Assuming cleaned_data should be a dictionary for subsequent passes and final output
        cleaned_data = self.json_cleaner.clean_parsed_json(parsed_data.dict())
        
        return cleaned_data

class LLMPassPipeline:
    """
    Manages a sequence of LLM passes.
    """
    def __init__(self, passes: List[BaseLLMPass]):
        self.passes = passes

    def run_pipeline(self,
                     model_client: BaseModelClient,
                     slm_config: OpenAIConfig, # Specific config for SLM
                     llm_config: OpenAIConfig, # Specific config for LLM fallback
                     initial_content: str,
                     document_context: Dict[str, Any],
                     temperature: float = 0.0,
                     max_tokens: int = 16384,
                     attempts: int = 1,
                     enable_fallback: bool = False,
                     **kwargs) -> Dict[str, Any]:
        """
        Executes the sequence of LLM passes.

        The output of one pass becomes the input (as a stringified JSON)
        for the next pass's `input_content`.
        
        Includes retry logic for the primary model (SLM) and optional fallback to another (LLM).
        """
        current_content = initial_content
        final_output = {}
        
        for llm_pass in self.passes:
            pass_successful = False
            for attempt in range(attempts):
                try:
                    pass_output = llm_pass.run_pass(
                        model_client=model_client,
                        model_config=slm_config, # Always try SLM config first
                        input_content=current_content,
                        document_context=document_context,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    pass_successful = True
                    break # Exit attempts loop on success
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} for pass '{llm_pass.name}' with SLM failed: {e}")
            
            if not pass_successful and enable_fallback:
                logger.info(f"SLM failed for pass '{llm_pass.name}' after {attempts} attempts. Attempting with LLM fallback.")
                try:
                    pass_output = llm_pass.run_pass(
                        model_client=model_client,
                        model_config=llm_config, # Try LLM config as fallback
                        input_content=current_content,
                        document_context=document_context,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    pass_successful = True
                    logger.info(f"Pass '{llm_pass.name}' successful with LLM fallback.")
                except Exception as e:
                    logger.error(f"LLM fallback also failed for pass '{llm_pass.name}': {e}")
            
            if not pass_successful:
                raise ValueError(f"LLM pass '{llm_pass.name}' failed after all attempts and fallbacks.")

            current_content = json.dumps(pass_output) # Stringify for next pass's input
            final_output.update(pass_output) # Accumulate results

        return final_output
