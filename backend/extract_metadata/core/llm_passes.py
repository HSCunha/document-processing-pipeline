import json
from typing import List, Dict, Any, Type, Optional
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam

from extract_metadata.core.model_client import BaseModelClient
from extract_metadata.core.config import OpenAIConfig
from extract_metadata.core.logging import get_logger
from extract_metadata.core.parsing import JSONParser, JSONCleaner

logger = get_logger(__name__)


def get_system_prompt_02(language="en"):
 
    system_prompt_02 = """
You are a multilingual AI assistant specialized in JSON objects. 
Your output must always be in the form of **valid JSON** with proper syntax, including double quotes around all keys and values.
Your primary directive is to parse valid and accurate JSON ojects, without deviations, according to the outlined instructions.
If a value is not present in the document, use null.

## INSTRUCTIONS

You will receive a json object and you will convert it to the following JSON schema:

```json
{{
    "purpose": "'PURPOSE'. Format: str",
    "scope": "'SCOPE'. Format: str",
    "target_audience": "'Target Audience'. Format: str",
    "abbreviations": "'ABBREVIATIONS AND DEFINITIONS'. Format: str",
    "governing_quality_module_or_global_standard": "'Governing Quality Module / Global Standard'. Format: List",
    "governing_documents": "'Governing Documents'. Format: List",
    "related_documents": "'Related Documents'. Format: List",
    "referenced_documents": "'Referenced Documents'. Format: List",
    "external_references": "'External References'. Format: List"
}}
```

Document IDs are a combination of 2 to 4 letters (document subtype) and 7 digits (id) separated by a '-'. 
Document IDs examples: "QM-0000000", "STD-0000000", "SOP-0000000", "WP-0000000", "GUID-0000000", "FRM-0000000" or "ATT-0000000".

**Allways** keep the JSON keys in English language. 
**Never** translate the JSON text values, keep the text in the original language. 

## EXAMPLES

```json
Example 1:
{{
    "purpose": null,
    "scope": null,
    "target_audience": null,
    "abbreviations": null,
    "governing_quality_module_or_global_standard": null,
    "governing_documents": ["SOP-0000000"],
    "related_documents": null,
    "referenced_documents": null,
    "external_references": null
}}
```

```json
Example 2:
{{
    "purpose": "This Standard Operating Procedure describes the process and requirements for verification audits performed by global GxP auditors at Novartis internal sites, systems.",
    "scope": "2.1 Process Scope This SOP applies to verification audits of Corrective and Preventive Actions (CAPAs).  2.2 Out of Scope ... 2.3 Target Audience ...",
    "target_audience": "This procedure applies to the following functions/roles as a minimum:  | Function | Roles | | - | - | | Global GxP Audit | Global GxP Audit Planning |
",
    "abbreviations": "Refer to the QMS Glossary for terms that are not defined below. 5.1 Abbreviations ... 5.2 Definitions ...",
    "governing_quality_module_or_global_standard": [
        "QM-0000000",
        "STD-0000000"
    ],
    "governing_documents": [],
    "related_documents": ["SOP-0000000"],
    "referenced_documents": [
        "SOP-0000000",
        "WP-0000000",
        "SOP-0000000",
        "SOP-0000000"
    ],
    "external_references": []
}}
```
    """
    return system_prompt_02


class MetadataExtractionSchema(BaseModel):
    purpose: Optional[str]
    scope: Optional[str]
    target_audience: Optional[str]
    abbreviations: Optional[str]
    governing_quality_module_or_global_standard: Optional[List[str]]
    governing_documents: Optional[List[str]]
    related_documents: Optional[List[str]]
    referenced_documents: Optional[List[str]]
    external_references: Optional[List[str]]


class BaseLLMPass:
    """
    A single LLM interaction pass.
    """
    def __init__(self, name: str, output_schema: Type[BaseModel], json_cleaner: JSONCleaner):
        self.name = name
        self.output_schema = output_schema
        self.json_cleaner = json_cleaner

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
        language = document_context.get('language', 'en')
        system_prompt = get_system_prompt_02(language)
        
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ]
        return messages

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
            response_format=MetadataExtractionSchema,
            **kwargs
        )
        
        parsed_data = JSONParser.parse_and_validate(raw_response, MetadataExtractionSchema)
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
