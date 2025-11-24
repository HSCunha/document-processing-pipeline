import json
import re
from typing import Dict, Any, Tuple, Optional, Type
from pydantic import BaseModel, ValidationError

from extract_metadata.core.logging import get_logger
from extract_metadata.core.references import BaseReferenceExtractor, ReferenceExtractorRegistry

logger = get_logger(__name__)

class JSONParser:
    """
    Provides utilities for robust and safe JSON parsing, especially for
    LLM outputs that might contain common formatting errors.
    """

    @staticmethod
    def strip_json_code_block(text: str) -> str:
        """
        Strips markdown code block fences (```json\n...\n```) from the text.
        """
        text = text.strip()
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.endswith("```"):
            text = text[:-len("```")].strip()
        return text

    @staticmethod
    def attempt_fix_json(json_string: str) -> Dict[str, Any]:
        """
        Attempts to fix common JSON issues (e.g., single quotes, trailing commas)
        and then parses the string into a dictionary.

        Args:
            json_string (str): The input JSON-like string.

        Returns:
            Dict[str, Any]: The parsed JSON dictionary.

        Raises:
            json.JSONDecodeError: If unable to fix and parse the JSON string.
        """
        # Replace single quotes with double quotes
        fixed_string = json_string.replace("'", '"')
        # Remove trailing commas before a closing brace or bracket
        fixed_string = re.sub(r',(\s*[}\]])', r'\1', fixed_string)
        
        return json.loads(fixed_string)

    @staticmethod
    def parse_and_validate(json_string: str, schema: Type[BaseModel]) -> BaseModel:
        """
        Parses a JSON string, optionally fixes it, and validates against a Pydantic schema.

        Args:
            json_string (str): The input JSON string (potentially LLM output).
            schema (Type[BaseModel]): The Pydantic model to validate against.

        Returns:
            BaseModel: An instance of the validated Pydantic model.

        Raises:
            ValueError: If parsing or validation fails.
        """
        stripped_json = JSONParser.strip_json_code_block(json_string)
        
        try:
            parsed_data = JSONParser.attempt_fix_json(stripped_json)
            return schema.parse_obj(parsed_data)
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError: Failed to parse JSON: {e}. Original string: {stripped_json}")
            raise ValueError(f"Failed to parse JSON: {e}")
        except ValidationError as e:
            logger.error(f"ValidationError: Failed to validate JSON against schema {schema.__name__}: {e}. Data: {parsed_data}")
            raise ValueError(f"Failed to validate JSON: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON parsing/validation: {e}. Original string: {stripped_json}")
            raise ValueError(f"Unexpected error: {e}")

class JSONCleaner:
    """
    Cleans and processes a JSON dictionary, typically after initial parsing.
    Includes logic for replacing None values and applying reference extraction.
    """
    def __init__(self, reference_extractor_name: Optional[str] = None):
        self.reference_extractor_name = reference_extractor_name

    def replace_none_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replaces `None` values in a dictionary with appropriate default values
        based on their expected type (empty list for list keys, empty string for string keys).
        """
        # These key lists should eventually come from a schema or configuration
        str_keys = [
            'name', 'version', 'document_type', 'status', 'language', 'title',
            'global_doc_ind', 'purpose', 'scope', 'target_audience', 'abbreviations',
            'quality_system', 'process', 'scopes', 'entities', 'owner_department'
        ]

        list_keys = [
            'governing_quality_module_or_global_standard', 'related_documents',
            'referenced_documents', 'external_references', 'governing_documents'
        ]

        for key, value in data.items():
            if value is None:
                if key in list_keys:
                    data[key] = []
                elif key in str_keys:
                    data[key] = ''
            elif isinstance(value, list):
                data[key] = list(set(value)) # Remove duplicates from lists
        return data

    def apply_reference_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies a registered reference extractor to specific fields within the JSON data.
        """
        if not self.reference_extractor_name:
            logger.debug("No reference extractor name provided to JSONCleaner. Skipping reference extraction.")
            return data

        try:
            ExtractorClass = ReferenceExtractorRegistry.get_extractor(self.reference_extractor_name)
            extractor = ExtractorClass() # Assuming the extractor can be instantiated without specific config for now
        except ValueError as e:
            logger.warning(f"Reference extractor '{self.reference_extractor_name}' not found. Skipping reference extraction. Error: {e}")
            return data

        specific_keys = [
            'governing_quality_module_or_global_standard',
            'governing_documents',
            'related_documents',
            'referenced_documents',
            'external_references'
        ]

        for key in specific_keys:
            if key in data and data[key] is not None:
                # If the data is already a list, convert each item to string and extract references
                # If it's a single string, extract references directly
                if isinstance(data[key], list):
                    # Process each item in the list and then flatten and deduplicate
                    all_extracted_refs = []
                    for item in data[key]:
                        if isinstance(item, str):
                            all_extracted_refs.extend(extractor.extract_references(item))
                        else:
                            logger.warning(f"Skipping non-string item in list for key '{key}': {item}")
                    data[key] = list(set(all_extracted_refs))
                elif isinstance(data[key], str):
                    data[key] = extractor.extract_references(data[key])
                else:
                    logger.warning(f"Skipping non-string/non-list data for key '{key}': {data[key]}")
        return data

    def clean_parsed_json(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies a sequence of cleaning steps to an already parsed JSON dictionary.
        """
        cleaned_data = self.replace_none_values(parsed_data)
        final_data = self.apply_reference_extraction(cleaned_data)
        return final_data
