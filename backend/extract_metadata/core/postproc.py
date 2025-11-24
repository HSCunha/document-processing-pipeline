from typing import Dict, Any, List, Callable, Optional
from extract_metadata.core.schema import DocumentMetadata, Document
from extract_metadata.core.references import BaseReferenceExtractor, ReferenceExtractorRegistry
from extract_metadata.core.logging import get_logger

logger = get_logger(__name__)

class MetadataPostProcessor:
    """
    Applies various post-processing steps to the extracted DocumentMetadata.
    """
    def __init__(self, reference_extractor_name: Optional[str] = None):
        """
        Args:
            reference_extractor_name (Optional[str]): The name of the reference extractor
                                                     to use for applying to specific fields.
        """
        self.reference_extractor_name = reference_extractor_name
        self._reference_extractor: Optional[BaseReferenceExtractor] = None
        if self.reference_extractor_name:
            try:
                ExtractorClass = ReferenceExtractorRegistry.get_extractor(self.reference_extractor_name)
                self._reference_extractor = ExtractorClass() # Assuming the extractor can be instantiated without specific config for now
            except ValueError as e:
                logger.warning(f"Reference extractor '{self.reference_extractor_name}' not found. "
                               f"Reference post-processing will be skipped. Error: {e}")

    def apply_references_to_fields(self, metadata: DocumentMetadata) -> DocumentMetadata:
        """
        Applies the configured reference extractor to specific reference-related fields
        in the DocumentMetadata.
        """
        if not self._reference_extractor:
            return metadata

        # These keys mirror those in JSONCleaner.apply_reference_extraction for now.
        # Ideally, these would be derived from the DocumentMetadata schema or a configuration.
        specific_keys = [
            'governing_quality_module_or_global_standard',
            'governing_documents',
            'related_documents',
            'referenced_documents',
            'external_references'
        ]

        metadata_dict = metadata.dict()

        for key in specific_keys:
            if key in metadata_dict and metadata_dict[key] is not None:
                current_value = metadata_dict[key]
                extracted_refs = []
                if isinstance(current_value, list):
                    for item in current_value:
                        if isinstance(item, str):
                            extracted_refs.extend(self._reference_extractor.extract_references(item))
                        else:
                            logger.debug(f"Skipping non-string item in list for key '{key}': {item}")
                elif isinstance(current_value, str):
                    extracted_refs.extend(self._reference_extractor.extract_references(current_value))
                else:
                    logger.debug(f"Skipping non-string/non-list data for key '{key}': {current_value}")
                
                metadata_dict[key] = list(set(extracted_refs)) # Deduplicate and update

        return DocumentMetadata(**metadata_dict)

    def force_inject_filename_metadata(self, metadata: DocumentMetadata, filename_metadata: Dict[str, str]) -> DocumentMetadata:
        """
        Force-injects metadata extracted from the filename into the DocumentMetadata.
        """
        metadata_dict = metadata.dict()
        for key, value in filename_metadata.items():
            if key in DocumentMetadata.model_fields: # Check if key is part of the schema
                metadata_dict[key] = value
        return DocumentMetadata(**metadata_dict)

    # Placeholder for other post-processing steps (e.g., SOP-specific header extraction)
    # These will be implemented in plugins and called from the main pipeline.
