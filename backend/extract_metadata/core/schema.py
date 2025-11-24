from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Type, Union

class DocumentMetadata(BaseModel):
    """
    Canonical schema for extracted document metadata.
    This model represents the full set of metadata fields that can be extracted.
    """
    name: str = Field(..., description="Document name, typically from filename.")
    version: str = Field(..., description="Document version, typically from filename.")
    status: str = Field(..., description="Document status, typically from filename.")
    global_doc_ind: Optional[str] = Field(None, description="Global document indicator.")
    document_type: str = Field(..., description="Type of the document, typically from filename (e.g., SOP, Policy).")
    language: str = Field(..., description="Language of the document, typically from filename (e.g., en).")
    
    title: Optional[str] = Field(None, description="Title of the document.")
    purpose: Optional[str] = Field(None, description="Purpose of the document.")
    scope: Optional[str] = Field(None, description="Scope of the document.")
    target_audience: Optional[str] = Field(None, description="Intended target audience.")
    abbreviations: Optional[str] = Field(None, description="Abbreviations used in the document.")
    
    governing_quality_module_or_global_standard: List[str] = Field(default_factory=list, description="List of governing quality modules or global standards.")
    governing_documents: List[str] = Field(default_factory=list, description="List of governing documents.")
    related_documents: List[str] = Field(default_factory=list, description="List of related documents.")
    referenced_documents: List[str] = Field(default_factory=list, description="List of internal referenced documents.")
    external_references: List[str] = Field(default_factory=list, description="List of external references.")

    quality_system: Optional[str] = Field(None, description="Quality system associated with the document.")
    process: Optional[str] = Field(None, description="Process described by the document.")
    scopes: Optional[str] = Field(None, description="Additional scopes.")
    entities: Optional[str] = Field(None, description="Entities involved.")
    owner_department: Optional[str] = Field(None, description="Owning department.")

    class Config:
        extra = "allow" # Allow extra fields for flexibility if plugins add more


class Document(BaseModel):
    """
    Represents a document with its content and basic properties.
    This will serve as the input to the metadata extraction pipeline.
    """
    id: str = Field(..., description="Unique identifier for the document.")
    filename: str = Field(..., description="Original filename of the document.")
    text_content: str = Field(..., description="Main textual content of the document (e.g., markdown).")
    
    # Raw data from external sources, e.g., Azure Document Intelligence, PyMuPDF4LLM
    # This can contain 'md_di', 'md_py', 'paragraphs', 'header_governing_documents', etc.
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw data from document intelligence or parsing tools.")

    # Any initial metadata extracted before the main pipeline (e.g., from filename)
    initial_metadata: Dict[str, Any] = Field(default_factory=dict, description="Initial metadata extracted before main processing.")

    class Config:
        extra = "allow"

class SchemaMapper:
    """
    Maps a canonical DocumentMetadata object to a desired output format,
    allowing selection and renaming of fields.
    """
    def __init__(self, output_schema_map: Dict[str, str]):
        """
        Args:
            output_schema_map (Dict[str, str]): A dictionary where keys are
                canonical schema field names and values are the desired output
                field names. If a field from the canonical schema is not in
                the map, it will be excluded. If the value is the same as the key,
                the field is included with its original name.
        """
        self.output_schema_map = output_schema_map

    def map(self, metadata: DocumentMetadata) -> Dict[str, Any]:
        """
        Applies the schema mapping to a DocumentMetadata instance.

        Args:
            metadata (DocumentMetadata): The canonical metadata to map.

        Returns:
            Dict[str, Any]: A dictionary representing the mapped output.
        """
        output = {}
        metadata_dict = metadata.dict(exclude_unset=True) # Get dict, exclude fields that were not set

        for canonical_key, output_key in self.output_schema_map.items():
            if canonical_key in metadata_dict:
                output[output_key] = metadata_dict[canonical_key]
        return output

# Example default mapper, equivalent to original keys_to_display
# This will likely be moved to a plugin eventually (e.g., sop/schema_map.py)
DEFAULT_OUTPUT_SCHEMA_MAP = {
    "name": "name",
    "version": "version",
    "status": "status",
    "language": "language",
    "purpose": "purpose",
    "scope": "scope",
    "target_audience": "target_audience",
    "abbreviations": "abbreviations",
    "governing_quality_module_or_global_standard": "governing_quality_module_or_global_standard",
    "governing_documents": "governing_documents",
    "related_documents": "related_documents",
    "referenced_documents": "referenced_documents",
    "external_references": "external_references"
}

# Pre-instantiate a default mapper
default_schema_mapper = SchemaMapper(DEFAULT_OUTPUT_SCHEMA_MAP)
