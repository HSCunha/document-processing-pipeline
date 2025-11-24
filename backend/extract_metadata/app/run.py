import os
import sys
import argparse
import json
from typing import Dict, Any, Type, Optional

# Adjust path to import from the root of the 'backend' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

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

# Import the new PdfLoader
try:
    from extract_metadata.core.pdf_loader import PdfLoader
except ImportError:
    PdfLoader = None
    pass


# SOP Plugin components
from extract_metadata.plugins.sop.filename_parser import SOPFilenameParser
from extract_metadata.plugins.sop.references import SOPReferenceExtractor
from extract_metadata.plugins.sop.cleaning import SOPDocVersionRemover, SOPUncontrolledCopyRemover, SOPFrequentLineRemover
from extract_metadata.plugins.sop.passes import get_sop_llm_pipeline
from extract_metadata.plugins.sop.schema_map import sop_schema_mapper
from extract_metadata.plugins.sop.header_footer import SOPHeaderFooterExtractor
from extract_metadata.plugins.sop.fallback_regex import SOPRegexFallbackExtractor
from extract_metadata.plugins.sop.postproc import SOPPostProcessor

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

    config = MetadataExtractionConfig.load_config(language=language)
    document_loader: Type[BaseDocumentLoader] = DictLoader
    filename_parser = SOPFilenameParser()
    model_client = AzureOpenAIClient(config.slm_openai_config)

    sop_cleaning_pipeline = CleaningPipeline(cleaners=[
        PatternRemover(),
        SelectionTagReplacer(),
        SOPDocVersionRemover(),
        SOPUncontrolledCopyRemover(),
        SOPFrequentLineRemover(),
        ExcessBreakLineRemover(),
        MarkdownConverter()
    ])

    chunker = HeadTailChunker() # Default chunker
    llm_pass_pipeline = get_sop_llm_pipeline(reference_extractor_name="sop_ids")
    post_processor = SOPPostProcessor(reference_extractor_name="sop_ids")
    fallback_mechanism: Optional[BaseFallbackMechanism] = SOPRegexFallbackExtractor() # Instantiate the SOP-specific fallback

    metadata_total = {"global_document_ind": "Yes"}
    f1_metadata = {
        "title": "SOP Document Title",
        "quality_system": "QMS",
        "process": "Document Control",
        "scopes": "Internal",
        "entities": "All Departments",
        "owner_department": "QA"
    }

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

    config = MetadataExtractionConfig.load_config(language=language)
    document_loader: Type[BaseDocumentLoader] = DictLoader
    filename_parser = GenericFilenameParser()
    model_client = AzureOpenAIClient(config.slm_openai_config)

    generic_cleaning_pipeline = get_generic_cleaning_pipeline() # Uses generic cleaning pipeline factory
    chunker = HeadTailChunker() # Default chunker
    llm_pass_pipeline = get_generic_llm_pipeline(reference_extractor_name="generic_refs")
    post_processor = MetadataPostProcessor(reference_extractor_name="generic_refs")
    fallback_mechanism: Optional[BaseFallbackMechanism] = None # For a generic pipeline, we might not have a specific regex fallback

    metadata_total = {"global_document_ind": "No"}
    f1_metadata = {
        "title": "Generic Document",
        "quality_system": "",
        "process": "",
        "scopes": "",
        "entities": "",
        "owner_department": ""
    }

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
    """
    Main function to run the metadata extraction pipeline from the command line.
    """
    parser = argparse.ArgumentParser(description="Run the metadata extraction pipeline on a document.")
    parser.add_argument("--file", type=str, required=True, help="Path to the document file to process.")
    parser.add_argument("--pipeline", type=str, default="sop", choices=["sop", "generic"], help="The pipeline to use ('sop' or 'generic').")
    
    args = parser.parse_args()

    file_path = args.file
    pipeline_type = args.pipeline

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower().lstrip('.')
    
    if file_extension == 'pdf' and PdfLoader is None:
        logger.error("PdfLoader is not available. Please install the required dependencies.")
        sys.exit(1)

    try:
        # Determine which pipeline setup function to use
        if pipeline_type == "sop":
            pipeline = setup_sop_pipeline(language="en")
        else:
            pipeline = setup_generic_pipeline(language="en")

        # Get the appropriate loader and override the one in the pipeline
        loader_class = DocumentLoaderRegistry.get_loader(file_extension)
        pipeline.document_loader = loader_class

        logger.info(f"\n--- Running {pipeline_type.upper()} Pipeline on {file_path} ---")
        
        # The 'run' method expects the source, which for file-based loaders is the path
        metadata = pipeline.run(file_path, os.path.basename(file_path))
        
        if metadata:
            logger.info(f"Successfully Extracted Metadata: {json.dumps(metadata, indent=2)}")
        else:
            logger.error("Failed to extract metadata.")
            
    except ValueError as e:
        logger.error(f"Configuration or setup error: {e}")
    except Exception as e:
        logger.error(f"An error occurred during pipeline execution: {e}", exc_info=True)


if __name__ == "__main__":
    main()