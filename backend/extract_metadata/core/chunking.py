from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type

class BaseChunker(ABC):
    """
    Abstract base class for a text chunking strategy.
    """
    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[str]:
        """
        Splits the given text into chunks.

        Args:
            text (str): The input text to chunk.
            **kwargs: Additional parameters for chunking (e.g., chunk_size, overlap).

        Returns:
            List[str]: A list of text chunks.
        """
        pass

class HeadTailChunker(BaseChunker):
    """
    A chunker that takes the head and tail of the text,
    useful for capturing context from both ends.
    """
    def __init__(self, max_length: int = 160000, head_length: int = 80000):
        """
        Args:
            max_length (int): The maximum length of the text before chunking is applied.
            head_length (int): The length of the head and tail parts to keep.
                                The total length will be 2 * head_length.
        """
        if head_length * 2 > max_length:
            raise ValueError(f"2 * head_length ({2 * head_length}) cannot be greater than max_length ({max_length}) for HeadTailChunker.")
        self.max_length = max_length
        self.head_length = head_length

    def chunk(self, text: str, **kwargs) -> List[str]:
        if len(text) > self.max_length:
            # Original code implies 3 chunks, but only takes first and last 80k.
            # This creates a single string that combines head and tail.
            return [text[:self.head_length] + text[-self.head_length:]]
        return [text] # Return the original text as a single chunk if not exceeding max_length

# Could also have a registry for chunkers if more types are added.
