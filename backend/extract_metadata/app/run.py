import os
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json # Import json for pretty printing in main
from typing import Dict, Any, Type, Optional

# Core components
from extract_metadata.core.config import MetadataExtractionConfig
from extract_metadata.core.logging import get_logger
from extract_metadata.core.schema import Document, DocumentMetadata, SchemaMapper
from extract_metadata.core.loaders import BaseDocumentLoader, DocumentLoaderRegistry, DictLoader
from extract_metadata.core.cleaning import CleaningPipeline, PatternRemover, SelectionTagReplacer, ExcessBreakLineRemover, MarkdownConverter
from extract_metadata.core.chunking import HeadTailChunker
from extract_metadata.core.model_client import BaseModelClient, AzureOpenAIClient
from extract_metadata.core.llm_passes import LLMPassPipeline
from extract_metadata.core.postproc import MetadataPostProcessor
from extract_metadata.core.fallback import BaseFallbackMechanism

# SOP Plugin components
from extract_metadata.plugins.sop.filename_parser import SOPFilenameParser
from extract_metadata.plugins.sop.references import SOPReferenceExtractor
from extract_metadata.plugins.sop.cleaning import SOPDocVersionRemover, SOPUncontrolledCopyRemover, SOPFrequentLineRemover
from extract_metadata.plugins.sop.passes import get_sop_llm_pipeline # This factory includes SOP-specific JSONCleaner and schemas
from extract_metadata.plugins.sop.schema_map import sop_schema_mapper
from extract_metadata.plugins.sop.header_footer import SOPHeaderFooterExtractor # For SOP-specific post-processing
from extract_metadata.plugins.sop.fallback_regex import SOPRegexFallbackExtractor
from extract_metadata.plugins.sop.postproc import SOPPostProcessor # New import

# Generic Plugin components
from extract_metadata.plugins.generic.filename_parser import GenericFilenameParser
from extract_metadata.plugins.generic.cleaning import get_generic_cleaning_pipeline
from extract_metadata.plugins.generic.references import GenericReferenceExtractor
from extract_metadata.plugins.generic.passes import get_generic_llm_pipeline
from extract_metadata.plugins.generic.schema_map import generic_schema_mapper

# The main pipeline orchestrator
from extract_metadata.core.pipeline import MetadataPipeline

logger = get_logger(__name__)

def setup_sop_pipeline(language: str = "en") -> MetadataPipeline:
    """
    Sets up the metadata extraction pipeline specifically for SOP documents.
    """
    logger.info(f"Setting up SOP metadata extraction pipeline for language: {language}")

    # Load configuration
    config = MetadataExtractionConfig.load_config(language=language)

    # Initialize core components
    document_loader: Type[BaseDocumentLoader] = DictLoader # Use DictLoader for now, as original input was dict
    filename_parser = SOPFilenameParser()
    model_client = AzureOpenAIClient(config.slm_openai_config) # Client is reusable, config just holds params

    # --- Cleaning Pipeline ---
    # Combine generic and SOP-specific cleaners
    sop_cleaning_pipeline = CleaningPipeline(cleaners=[
        PatternRemover(), # Generic
        SelectionTagReplacer(), # Generic
        SOPDocVersionRemover(), # SOP specific
        SOPUncontrolledCopyRemover(), # SOP specific
        SOPFrequentLineRemover(), # SOP specific
        ExcessBreakLineRemover(), # Generic
        MarkdownConverter() # Generic
    ])

    chunker = HeadTailChunker() # Default chunker

    # --- LLM Pass Pipeline ---
    # The get_sop_llm_pipeline handles JSONCleaner internally with "sop_ids"
    llm_pass_pipeline = get_sop_llm_pipeline(reference_extractor_name="sop_ids")

    # --- Post Processor ---
    # Use SOP-specific post-processor
    post_processor = SOPPostProcessor(reference_extractor_name="sop_ids") # Pass reference extractor name

    # --- Fallback Mechanism ---
    fallback_mechanism: Optional[BaseFallbackMechanism] = SOPRegexFallbackExtractor() # Instantiate the SOP-specific fallback

    # External metadata placeholders (from original get_metadata signature)
    # These would typically come from other parts of the system or configuration
    metadata_total = {"global_document_ind": "Yes"}
    f1_metadata = {
        "title": "SOP Document Title",
        "quality_system": "QMS",
        "process": "Document Control",
        "scopes": "Internal",
        "entities": "All Departments",
        "owner_department": "QA"
    }

    # Assemble the pipeline
    pipeline = MetadataPipeline(
        config=config,
        document_loader=document_loader,
        filename_parser=filename_parser,
        cleaning_pipeline=sop_cleaning_pipeline,
        chunker=chunker,
        model_client=model_client,
        llm_pass_pipeline=llm_pass_pipeline,
        post_processor=post_processor,
        schema_mapper=sop_schema_mapper,
        metadata_total=metadata_total,
        f1_metadata=f1_metadata,
        fallback_mechanism=fallback_mechanism # Pass the fallback mechanism
    )
    
    return pipeline

def setup_generic_pipeline(language: str = "en") -> MetadataPipeline:
    """
    Sets up a generic metadata extraction pipeline.
    """
    logger.info(f"Setting up Generic metadata extraction pipeline for language: {language}")

    # Load configuration
    config = MetadataExtractionConfig.load_config(language=language)

    # Initialize core components
    document_loader: Type[BaseDocumentLoader] = DictLoader
    filename_parser = GenericFilenameParser()
    model_client = AzureOpenAIClient(config.slm_openai_config)

    # --- Cleaning Pipeline ---
    generic_cleaning_pipeline = get_generic_cleaning_pipeline() # Uses generic cleaning pipeline factory

    chunker = HeadTailChunker() # Default chunker

    # --- LLM Pass Pipeline ---
    llm_pass_pipeline = get_generic_llm_pipeline(reference_extractor_name="generic_refs")

    # --- Post Processor ---
    post_processor = MetadataPostProcessor(reference_extractor_name="generic_refs")

    # --- Fallback Mechanism (Optional for generic) ---
    # For a generic pipeline, we might not have a specific regex fallback, so it can be None
    fallback_mechanism: Optional[BaseFallbackMechanism] = None 

    # External metadata placeholders
    metadata_total = {"global_document_ind": "No"}
    f1_metadata = {
        "title": "Generic Document",
        "quality_system": "",
        "process": "",
        "scopes": "",
        "entities": "",
        "owner_department": ""
    }

    # Assemble the pipeline
    pipeline = MetadataPipeline(
        config=config,
        document_loader=document_loader,
        filename_parser=filename_parser,
        cleaning_pipeline=generic_cleaning_pipeline,
        chunker=chunker,
        model_client=model_client,
        llm_pass_pipeline=llm_pass_pipeline,
        post_processor=post_processor,
        schema_mapper=generic_schema_mapper,
        metadata_total=metadata_total,
        f1_metadata=f1_metadata,
        fallback_mechanism=fallback_mechanism # Pass the fallback mechanism
    )
    
    return pipeline


def main():
    # Example usage:
    # Set environment variables for testing or use a .env file
    # os.environ["AZURE_OPENAI_ENDPOINT"] = "YOUR_ENDPOINT"
    # os.environ["AZURE_OPENAI_SLM"] = "gpt-4"
    # os.environ["AZURE_OPENAI_SLM_API_VERSION"] = "2024-02-15-preview"
    # os.environ["SLM_EXTRACTION_ATTEMPTS"] = "1"
    # os.environ["ENABLE_LLM"] = "False"

    print("Make sure to configure the following environment variables:")
    print("- AZURE_OPENAI_ENDPOINT: The endpoint for your Azure OpenAI service.")
    print("- AZURE_OPENAI_SLM: The deployment name for your SLM model.")
    print("- AZURE_OPENAI_SLM_API_VERSION: The API version for your SLM model.")
    # --- SOP Pipeline Example ---
    sop_pipeline = setup_sop_pipeline(language="en")

    # Mock document input (similar to original 'document' parameter)
    mock_sop_document_source = {
        "md_di": "This is a sample SOP document. Doc No. : SOP-1234567 Version : 1.0. "
                 "This document defines the process for QM-9876543. "
                 "Uncontrolled Copy. Related to STD-1122334. <!-- PageFooter=\"Example\" -->",
        "paragraphs": [
            {"content": "Header text with another reference: ATT-0000001", "boundingRegions": [{"pageNumber": 2, "polygon": [0,0,1,1,1,1.5,0,1.5]}]}
        ]
    }
    sop_filename = "SOP-1234567_1.0_Draft_No_SOP_en.pdf"

    logger.info("\n--- Running SOP Pipeline ---")
    try:
        sop_metadata = sop_pipeline.run(mock_sop_document_source, sop_filename)
        if sop_metadata:
            logger.info(f"SOP Extracted Metadata: {json.dumps(sop_metadata, indent=2)}")
        else:
            logger.error("Failed to extract SOP metadata.")
    except Exception as e:
        logger.error(f"Error during SOP pipeline run: {e}", exc_info=True)


    # --- Generic Pipeline Example ---
    generic_pipeline = setup_generic_pipeline(language="en")

    mock_generic_document_source = {
        "md_di": "This is a generic document about product development. It covers various stages. "
                 "Keywords include: innovation, design, testing. Visit https://example.com/info for more."
    }
    generic_filename = "Product_Development_v2.1.docx"

    logger.info("\n--- Running Generic Pipeline ---")
    try:
        generic_metadata = generic_pipeline.run(mock_generic_document_source, generic_filename)
        if generic_metadata:
            logger.info(f"Generic Extracted Metadata: {json.dumps(generic_metadata, indent=2)}")
        else:
            logger.warning("Could not extract Generic metadata.")
    except Exception as e:
        logger.error(f"Error during Generic pipeline run: {e}", exc_info=True)


if __name__ == "__main__":
    main()
