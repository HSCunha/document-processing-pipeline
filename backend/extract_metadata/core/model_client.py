from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import logging

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from extract_metadata.core.config import OpenAIConfig
from extract_metadata.core.logging import get_logger

logger = get_logger(__name__)

class BaseModelClient(ABC):
    """
    Abstract base class for LLM model clients.
    """
    @abstractmethod
    def generate(
        self,
        messages: List[ChatCompletionMessageParam],
        model_name: str,
        temperature: float = 0.0,
        max_tokens: int = 16384,
        response_format: Optional[Any] = None, # Pydantic model for structured output
        **kwargs
    ) -> str:
        """
        Generates a response from the LLM based on the given messages.

        Args:
            messages (List[ChatCompletionMessageParam]): A list of message objects for the conversation.
            model_name (str): The name of the model to use.
            temperature (float): Controls randomness in the output.
            max_tokens (int): The maximum number of tokens to generate.
            response_format (Optional[Any]): Pydantic model for structured output.
            **kwargs: Additional parameters specific to the model client.

        Returns:
            str: The generated text response.
        """
        pass

class AzureOpenAIClient(BaseModelClient):
    """
    Client for interacting with Azure OpenAI services.
    """
    def __init__(self, config: OpenAIConfig):
        self.config = config
        self._client: Optional[AzureOpenAI] = None

    def _initialize_client(self):
        """Initializes the AzureOpenAI client with credentials."""
        if self._client is None:
            if not self.config.endpoint or not self.config.api_version:
                raise ValueError("Azure OpenAI endpoint and API version must be configured.")
            
            api_key = os.environ.get("AZURE_OPENAI_KEY")
            
            try:
                if api_key:
                    self._client = AzureOpenAI(
                        azure_endpoint=self.config.endpoint,
                        api_version=self.config.api_version,
                        api_key=api_key
                    )
                    logger.info(f"AzureOpenAI client initialized with API key for endpoint: {self.config.endpoint}")
                else:
                    # DefaultAzureCredential will try various authentication methods (env, managed identity, etc.)
                    credential = DefaultAzureCredential()
                    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
                    
                    self._client = AzureOpenAI(
                        azure_endpoint=self.config.endpoint,
                        api_version=self.config.api_version,
                        azure_ad_token_provider=token_provider
                    )
                    logger.info(f"AzureOpenAI client initialized with Azure AD for endpoint: {self.config.endpoint}")
            except Exception as e:
                logger.error(f"Failed to initialize AzureOpenAI client: {e}")
                self._client = None
                raise

    @property
    def client(self) -> AzureOpenAI:
        if self._client is None:
            self._initialize_client()
        return self._client

    def generate(
        self,
        messages: List[ChatCompletionMessageParam],
        model_name: str,
        temperature: float = 0.0,
        max_tokens: int = 16384,
        response_format: Optional[Any] = None,
        **kwargs
    ) -> str:
        """
        Generates a response from the Azure OpenAI LLM.
        """
        if self.client is None:
            raise RuntimeError("AzureOpenAI client is not initialized.")
            
        try:
            completion = self.client.beta.chat.completions.parse(
                model=model_name, # Use the model_name passed to the generate method
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
                **kwargs
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error during Azure OpenAI generation with model '{model_name}': {e}")
            raise
