from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseFallbackMechanism(ABC):
    """
    Abstract base class for a fallback mechanism in case primary extraction methods fail.
    """
    @abstractmethod
    def extract(self, document_context: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Attempts to extract metadata using a fallback strategy.

        Args:
            document_context (Dict[str, Any]): The document context, including its content.
            **kwargs: Additional parameters needed for the fallback extraction.

        Returns:
            Optional[Dict[str, Any]]: Extracted metadata if successful, otherwise None.
        """
        pass
