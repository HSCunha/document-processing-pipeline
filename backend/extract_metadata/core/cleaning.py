from abc import ABC, abstractmethod
import re
from typing import List, Dict, Any, Type, Optional
from collections import Counter
from markdownify import markdownify # Assuming markdownify is installed and generally useful
from extract_metadata.core.config import CleaningConfig
from extract_metadata.core.logging import get_logger

logger = get_logger(__name__)

class BaseCleaner(ABC):
    """
    Abstract base class for a text cleaning step.
    Each cleaner takes text and returns cleaned text.
    """
    @abstractmethod
    def clean(self, text: str, config: Optional[CleaningConfig] = None) -> str:
        """
        Applies a cleaning transformation to the input text.

        Args:
            text (str): The input text to clean.
            config (Optional[CleaningConfig]): Configuration for cleaning operations.

        Returns:
            str: The cleaned text.
        """
        pass

class CleaningPipeline:
    """
    Manages a sequence of cleaning steps to be applied to text.
    """
    def __init__(self, cleaners: List[BaseCleaner]):
        self.cleaners = cleaners

    def clean(self, text: str, config: Optional[CleaningConfig] = None) -> str:
        """
        Applies all cleaners in the pipeline sequentially to the text.
        """
        for cleaner in self.cleaners:
            text = cleaner.clean(text, config)
        return text

class PatternRemover(BaseCleaner):
    """
    Removes patterns defined in a list of regexes.
    Uses `patterns_to_remove` from CleaningConfig.
    """
    def clean(self, text: str, config: Optional[CleaningConfig] = None) -> str:
        if not config or not config.cleaning.patterns_to_remove:
            return text
        for pattern in config.cleaning.patterns_to_remove:
            text = re.sub(pattern, "", text, flags=re.DOTALL)
        return text

class SelectionTagReplacer(BaseCleaner):
    """
    Replaces selection tags based on mappings defined in CleaningConfig.
    Uses `selection_mappings` from CleaningConfig.
    """
    def clean(self, text: str, config: Optional[CleaningConfig] = None) -> str:
        if not config or not config.cleaning.selection_mappings:
            return text
        for key, value in config.cleaning.selection_mappings.items():
            text = re.sub(key, value, text)
        return text

class ExcessBreakLineRemover(BaseCleaner):
    """
    Replaces three or more consecutive newlines with exactly two newlines.
    """
    def clean(self, text: str, config: Optional[CleaningConfig] = None) -> str:
        return re.sub(r'(\n\s*){3,}', '\n\n', text)

class MarkdownConverter(BaseCleaner):
    """
    Converts HTML mixed content to Markdown using markdownify.
    This step is usually applied at the end of cleaning.
    """
    def clean(self, text: str, config: Optional[CleaningConfig] = None) -> str:
        try:
            return markdownify(text)
        except ImportError:
            logger.warning("markdownify not installed, skipping HTML to Markdown conversion.")
            return text
        except Exception as e:
            logger.error(f"Error during markdownify conversion: {e}")
            return text
