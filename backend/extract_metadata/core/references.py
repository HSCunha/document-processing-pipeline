from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, Optional, Callable
import re

class BaseReferenceExtractor(ABC):
    """
    Abstract base class for extracting references from text.
    """
    @abstractmethod
    def extract_references(self, text: str, **kwargs) -> List[str]:
        """
        Extracts references from the given text.

        Args:
            text (str): The input text to search for references.
            **kwargs: Additional parameters for extraction.

        Returns:
            List[str]: A list of extracted and normalized references.
        """
        pass

class ReferenceExtractorRegistry:
    """
    A registry to manage different reference extractors.
    """
    _extractors: Dict[str, Type[BaseReferenceExtractor]] = {}

    @classmethod
    def register_extractor(cls, extractor_type: str, extractor_class: Type[BaseReferenceExtractor]):
        """
        Registers a new reference extractor.

        Args:
            extractor_type (str): A unique string identifier for the extractor (e.g., "sop_ids", "urls").
            extractor_class (Type[BaseReferenceExtractor]): The class of the extractor to register.
        """
        if not issubclass(extractor_class, BaseReferenceExtractor):
            raise ValueError(f"Extractor class must inherit from BaseReferenceExtractor: {extractor_class.__name__}")
        cls._extractors[extractor_type] = extractor_class

    @classmethod
    def get_extractor(cls, extractor_type: str) -> Type[BaseReferenceExtractor]:
        """
        Retrieves a registered reference extractor by its type.

        Args:
            extractor_type (str): The string identifier of the extractor.

        Returns:
            Type[BaseReferenceExtractor]: The class of the requested extractor.

        Raises:
            ValueError: If no extractor is registered for the given type.
        """
        extractor = cls._extractors.get(extractor_type)
        if not extractor:
            raise ValueError(f"No reference extractor registered for type: {extractor_type}")
        return extractor

    @classmethod
    def list_extractors(cls) -> List[str]:
        """Lists all registered extractor types."""
        return list(cls._extractors.keys())

class RegexReferenceExtractor(BaseReferenceExtractor):
    """
    A generic reference extractor that uses a list of regex patterns.
    """
    def __init__(self, patterns: List[str], standardize_func: Optional[Callable[[str], str]] = None):
        """
        Args:
            patterns (List[str]): A list of regex patterns to search for.
            standardize_func (Optional[Callable[[str], str]]): A function to apply to each found match for standardization.
        """
        self.patterns = patterns
        self.standardize_func = standardize_func

    def extract_references(self, text: str, **kwargs) -> List[str]:
        all_matches = []
        try:
            for pattern in self.patterns:
                matches = re.findall(pattern, text)
                if self.standardize_func:
                    matches = [self.standardize_func(match) for match in matches]
                all_matches.extend(matches)
        except Exception:
            # Catch all exceptions and return empty list, as in original
            all_matches = []
        return list(set(all_matches)) # Deduplicate references
