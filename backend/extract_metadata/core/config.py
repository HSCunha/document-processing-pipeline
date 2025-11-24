from pydantic import BaseModel, Field, SecretStr
from typing import List, Dict, Any, Optional, Type
import os
import logging

# Configure basic logging for the config module
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class CleaningConfig(BaseModel):
    patterns_to_remove: List[str] = Field(
        default=[
            r"<figure>.*?</figure>",
            r"<!-- PageFooter=\".*?\" -->",
            r"<!-- PageHeader=\".*?\" -->"
        ],
        description="Regex patterns to remove from the markdown text."
    )
    doc_no_regex: str = Field(r"Doc No\. : \w{3}-\d+", description="Regex for document number.")
    version_regex: str = Field(r"Version : \d+\.\d+", description="Regex for document version.")
    uncontrolled_copy_regex: str = Field(r"Uncontrolled Copy", description="Regex for uncontrolled copy.")
    length_threshold: int = Field(10, description="Minimum length for a 'long line' in cleaning.")
    frequency_threshold: int = Field(10, description="Minimum frequency count for a frequent line in cleaning.")
    selection_mappings: Dict[str, str] = Field(
        default_factory=lambda: {":selected:": "☒", ":unselected:": "☐"},
        description="Mappings for selection tags."
    )

class OpenAIConfig(BaseModel):
    """Configuration for an OpenAI-compatible LLM provider."""
    model_name_env_var_base: str = Field(..., description="Base name for environment variable storing the model name (e.g., 'AZURE_OPENAI_SLM').")
    api_version_env_var_base: str = Field(..., description="Base name for environment variable storing the API version (e.g., 'AZURE_OPENAI_SLM_API_VERSION').")
    endpoint_env_var: str = Field("AZURE_OPENAI_ENDPOINT", description="Environment variable storing the OpenAI-compatible endpoint URL.")
    
    # These fields will be populated dynamically from environment variables
    model_name: Optional[str] = None
    api_version: Optional[str] = None
    endpoint: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True # Allows types like DefaultAzureCredential if they were part of config

    def load_from_env(self, language: str = "en"):
        """Loads model name, API version, and endpoint from environment variables, considering language-specific overrides."""
        
        # Attempt language-specific overrides
        lang_model_name = os.getenv(f"{self.model_name_env_var_base}_{language.upper()}")
        lang_api_version = os.getenv(f"{self.api_version_env_var_base}_{language.upper()}")
        
        if lang_model_name and lang_api_version:
            self.model_name = lang_model_name
            self.api_version = lang_api_version
        else:
            # Fallback to general settings
            self.model_name = os.getenv(self.model_name_env_var_base)
            self.api_version = os.getenv(self.api_version_env_var_base)
            
        self.endpoint = os.getenv(self.endpoint_env_var)

        if not self.model_name or not self.api_version or not self.endpoint:
            logging.warning(
                f"Incomplete LLM configuration for base variables "
                f"'{self.model_name_env_var_base}' and '{self.api_version_env_var_base}': "
                f"model_name={self.model_name}, api_version={self.api_version}, endpoint={self.endpoint}"
            )
            print("The following environment variables are not configured:")
            print(f"- {self.model_name_env_var_base}: The deployment name for your SLM model.")
            print(f"- {self.api_version_env_var_base}: The API version for your SLM model.")
            print(f"- {self.endpoint_env_var}: The endpoint for your Azure OpenAI service.")

class LoaderConfig(BaseModel):
    name: str = Field("dict", description="Name of the loader to use (e.g., 'dict', 'pdf').")
    options: Dict[str, Any] = Field(default_factory=dict, description="Options specific to the loader.")

class MetadataExtractionConfig(BaseModel):
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig, description="Configuration for text cleaning.")
    
    # LLM Provider Configuration
    slm_openai_config: OpenAIConfig = Field(
        default_factory=lambda: OpenAIConfig(
            model_name_env_var_base="AZURE_OPENAI_SLM",
            api_version_env_var_base="AZURE_OPENAI_SLM_API_VERSION"
        ),
        description="Settings for the SLM OpenAI provider."
    )
    llm_openai_config: OpenAIConfig = Field(
        default_factory=lambda: OpenAIConfig(
            model_name_env_var_base="AZURE_OPENAI_LLM",
            api_version_env_var_base="AZURE_OPENAI_LLM_API_VERSION"
        ),
        description="Settings for the LLM OpenAI provider (fallback)."
    )

    slm_extraction_attempts: int = Field(3, description="Number of attempts to extract metadata with SLM.")
    enable_llm_fallback: bool = Field(False, description="Enable fallback to LLM if SLM extraction fails.")

    # Other configurations that might be global
    default_language: str = Field("en", description="Default language for extraction.")

    # New loader configuration
    loader: LoaderConfig = Field(default_factory=lambda: LoaderConfig(name="dict"), description="Configuration for the document loader.")

    class Config:
        env_file = ".env"
        extra = "ignore"
        env_prefix = ""


    def __init__(self, **data: Any):
        super().__init__(**data)
        # Manually load environment variables for direct fields as Pydantic's env_prefix might not catch all
        self.slm_extraction_attempts = int(os.getenv("SLM_EXTRACTION_ATTEMPTS", str(self.slm_extraction_attempts)))
        self.enable_llm_fallback = os.getenv("ENABLE_LLM", str(self.enable_llm_fallback)).lower() == "true"
        self.default_language = os.getenv("DEFAULT_LANGUAGE", self.default_language)

    @classmethod
    def load_config(cls, language: Optional[str] = None) -> "MetadataExtractionConfig":
        """
        Loads the configuration, including dynamic LLM settings based on the provided language.
        If language is None, uses default_language from config or "en".
        """
        config = cls()
        effective_language = language if language is not None else config.default_language
        
        config.slm_openai_config.load_from_env(language=effective_language)
        config.llm_openai_config.load_from_env(language=effective_language)
        
        return config