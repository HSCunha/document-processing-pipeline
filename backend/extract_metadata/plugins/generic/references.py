from typing import List
import re

from extract_metadata.core.references import BaseReferenceExtractor, ReferenceExtractorRegistry, RegexReferenceExtractor
from extract_metadata.core.logging import get_logger

logger = get_logger(__name__)

GENERIC_REFERENCE_PATTERNS = [
    r"https?:\/\/[^\s]+",  # URLs
    r"\b\w+\.(?:pdf|docx|xlsx|pptx|txt|csv|json|xml|html|mp4|mp3|zip)\b", # Common file extensions
]

def standardize_generic_reference(match: str) -> str:
    """A generic standardization function (e.g., lowercasing, stripping)."""
    return match.strip()

class GenericReferenceExtractor(RegexReferenceExtractor):
    """
    Generic reference extractor that uses common patterns for files and URLs.
    """
    def __init__(self):
        super().__init__(patterns=GENERIC_REFERENCE_PATTERNS, standardize_func=standardize_generic_reference)

# Register the GenericReferenceExtractor
ReferenceExtractorRegistry.register_extractor("generic_refs", GenericReferenceExtractor)
