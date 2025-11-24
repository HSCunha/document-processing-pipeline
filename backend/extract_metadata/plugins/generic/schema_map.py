from typing import Dict, Any
from extract_metadata.core.schema import SchemaMapper

GENERIC_OUTPUT_SCHEMA_MAP: Dict[str, str] = {
    "name": "name",
    "version": "version",
    "status": "status",
    "document_type": "document_type",
    "language": "language",
    "summary": "summary",
    "keywords": "keywords"
}

# Instantiate a SchemaMapper for generic output
generic_schema_mapper = SchemaMapper(GENERIC_OUTPUT_SCHEMA_MAP)
