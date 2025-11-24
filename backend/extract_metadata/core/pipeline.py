import os
from typing import Dict, Any, Optional, Type, List

from extract_metadata.core.config import MetadataExtractionConfig
from extract_metadata.core.logging import get_logger
from extract_metadata.core.schema import Document, DocumentMetadata, SchemaMapper
from extract_metadata.core.loaders import BaseDocumentLoader, DocumentLoaderRegistry
from extract_metadata.core.cleaning import CleaningPipeline
from extract_metadata.core.chunking import BaseChunker, HeadTailChunker
from extract_metadata.core.model_client import BaseModelClient, AzureOpenAIClient
from extract_metadata.core.llm_passes import LLMPassPipeline
from extract_metadata.core.fallback import BaseFallbackMechanism
from extract_metadata.core.postproc import MetadataPostProcessor

logger = get_logger(__name__)

class MetadataPipeline:
    """
    Orchestrates the entire metadata extraction process.
    """
    def __init__(
        self,
        config: MetadataExtractionConfig,
        document_loader: Type[BaseDocumentLoader], # Expecting the class, not an instance
        filename_parser: Any, # Will be an interface later
        cleaning_pipeline: CleaningPipeline,
        chunker: BaseChunker,
        model_client: BaseModelClient,
        llm_pass_pipeline: LLMPassPipeline,
        post_processor: MetadataPostProcessor,
        schema_mapper: SchemaMapper,
        metadata_total: Dict[str, Any], # Placeholder for external metadata like global_document_ind, quality_system etc.
        f1_metadata: Dict[str, Any], # Placeholder for external metadata like title, process etc.
        fallback_mechanism: Optional[BaseFallbackMechanism] = None
    ):
        self.config = config
        self.document_loader = document_loader # Store the class
        self.filename_parser = filename_parser
        self.cleaning_pipeline = cleaning_pipeline
        self.chunker = chunker
        self.model_client = model_client
        self.llm_pass_pipeline = llm_pass_pipeline
        self.post_processor = post_processor
        self.schema_mapper = schema_mapper
        self.metadata_total = metadata_total
        self.f1_metadata = f1_metadata
        self.fallback_mechanism = fallback_mechanism

    def run(self, raw_document_source: Any, filename: str) -> Optional[Dict[str, Any]]:
        """
        Runs the metadata extraction pipeline for a given document.

        Args:
            raw_document_source (Any): The raw source of the document (e.g., dict, file path).
            filename (str): The filename associated with the document.

        Returns:
            Optional[Dict[str, Any]]: The extracted metadata as a dictionary, or None if an error occurs.
        """
        try:
            # 1. Load the document
            # Instantiate the loader here as it might need fresh state per document
            loader_instance = self.document_loader() 
            document: Document = loader_instance.load(raw_document_source, filename)
            logger.info(f"Document '{document.filename}' loaded successfully with ID: {document.id}.")

            # 2. Extract initial metadata from filename
            filename_metadata = self.filename_parser.parse(document.filename)
            document.initial_metadata.update(filename_metadata)
            document.language = document.initial_metadata.get("language", self.config.default_language)
            document.document_type = document.initial_metadata.get("document_type", "unknown")

            # 3. Clean the document content
            cleaned_markdown = self.cleaning_pipeline.clean(document.text_content, self.config)
            logger.info(f"Document '{document.filename}' cleaned.")

            # 4. Chunk the document content
            chunks = self.chunker.chunk(cleaned_markdown)
            # Assuming for now we take the first chunk if multiple are returned
            processed_content_for_llm = chunks[0] if chunks else "" 
            logger.info(f"Document '{document.filename}' chunked. Length of content for LLM: {len(processed_content_for_llm)}")

            # 5. Execute LLM passes
            # The original code uses a general 'model' dict. Now we have slm_openai_config and llm_openai_config
            # which are populated dynamically. We need to ensure they are loaded for the current document language.
            self.config.slm_openai_config.load_from_env(language=document.language) # Ensure configs are loaded for specific language
            self.config.llm_openai_config.load_from_env(language=document.language)

            try:
                llm_extracted_metadata_dict = self.llm_pass_pipeline.run_pipeline(
                    model_client=self.model_client,
                    slm_config=self.config.slm_openai_config,
                    llm_config=self.config.llm_openai_config,
                    initial_content=processed_content_for_llm,
                    document_context=document.dict(), # Pass the document object as context
                    temperature=0.0, # Hardcoded in original
                    max_tokens=16384, # Hardcoded in original
                    attempts=self.config.slm_extraction_attempts,
                    enable_fallback=self.config.enable_llm_fallback
                ) or {} # Ensure it's a dict even if None is returned
                logger.info(f"LLM passes completed for '{document.filename}'. Result: {'Success' if llm_extracted_metadata_dict else 'Failure'}")
            except ValueError as e:
                logger.warning(f"LLM pass pipeline failed for '{document.filename}': {e}")
                llm_extracted_metadata_dict = {}
            
            # If LLM extraction failed, try the fallback mechanism if it's configured
            if not llm_extracted_metadata_dict and self.fallback_mechanism:
                logger.warning(f"LLM extraction failed for '{document.filename}'. Attempting fallback if configured.")
                fallback_result = self.fallback_mechanism.extract(
                    document_context=document.dict(), 
                    f1_metadata=self.f1_metadata
                )
                if fallback_result:
                    llm_extracted_metadata_dict = fallback_result
                    logger.info(f"Fallback extraction successful for '{document.filename}'.")
                else:
                    logger.error(f"Fallback extraction also failed for '{document.filename}'.")
            elif not llm_extracted_metadata_dict:
                 logger.error(f"LLM extraction failed for '{document.filename}' and no fallback mechanism is configured.")
                 raise ValueError("Metadata extraction failed: LLM failed and no fallback configured.")

            # Ensure there are no overlapping keys with what we already have from the filename.
            llm_extracted_metadata_dict = {k: v for k, v in llm_extracted_metadata_dict.items() if k not in document.initial_metadata}
            
            # Combine initial filename metadata with LLM extracted metadata
            intermediate_metadata = DocumentMetadata(
                **document.initial_metadata, # Start with initial metadata
                **llm_extracted_metadata_dict # Overlay LLM extracted data
            )

            # Add other f1_metadata and metadata_total fields.
            # These are external to the document itself, so they are added here.
            intermediate_metadata.global_doc_ind = self.metadata_total.get("global_document_ind")
            intermediate_metadata.title = self.f1_metadata.get("title")
            intermediate_metadata.quality_system = self.f1_metadata.get("quality_system")
            intermediate_metadata.process = self.f1_metadata.get("process")
            intermediate_metadata.scopes = self.f1_metadata.get("scopes")
            intermediate_metadata.entities = self.f1_metadata.get("entities")
            intermediate_metadata.owner_department = self.f1_metadata.get("owner_department")

            # 6. Apply post-processing (e.g., specific header extraction, final reference extraction)
            # This is where SOP-specific get_governing_documents_from_header would be plugged in.
            
            # The post_processor instance passed to the pipeline might contain plugin-specific logic
            processed_metadata = self.post_processor.apply_references_to_fields(intermediate_metadata)
            processed_metadata = self.post_processor.force_inject_filename_metadata(processed_metadata, filename_metadata)

            logger.info(f"Post-processing completed for '{document.filename}'.")

            # 7. Map to final output schema
            final_output = self.schema_mapper.map(processed_metadata)
            logger.info(f"Metadata extracted for '{document.filename}'.")
            
            return final_output

        except Exception as e:
            logger.error(f"Error extracting metadata for '{filename}': {e}", exc_info=True)
            return None
