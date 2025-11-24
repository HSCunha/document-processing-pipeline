import os
import re # Import re for regex in GenericFilenameParser
from typing import Dict, Any, Optional

from extract_metadata.core.logging import get_logger
from extract_metadata.plugins.sop.filename_parser import BaseFilenameParser # Reusing BaseFilenameParser

logger = get_logger(__name__)

class GenericFilenameParser(BaseFilenameParser):
    """
    A generic filename parser that extracts basic information or returns defaults.
    Serves as a fallback or for documents without specific naming conventions.
    """
    def parse(self, filename: str) -> Dict[str, str]:
        base_filename = os.path.splitext(filename)[0]
        # Example: if filename is "document_v1.0.pdf", extract "document" as name, "1.0" as version
        name = base_filename
        version = ""
        
        # Simple attempt to extract version
        match = re.search(r"[vV]?(\d+\.\d+(?:\.\d+)*)", base_filename) # Added (?:\\.\d+)* for optional patch versions
        if match:
            version = match.group(1)
            # Remove the matched version string from the name, handling common separators
            name = re.sub(r"[_\-.]*[vV]?\d+\.\d+(?:\.\d+)*", "", base_filename, count=1).strip("_.-")
            if not name: # If only version was present
                name = base_filename
        
        # Default to "unknown" if name is empty after processing
        if not name:
            name = "unknown"

        return {
            "name": name,
            "version": version,
            "status": "unknown",
            "global_doc_ind": "No", # Default value
            "document_type": "generic",
            "language": "en" # Default to English
        }
