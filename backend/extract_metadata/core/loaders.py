from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List, Optional
from extract_metadata.core.schema import Document
import uuid

class BaseDocumentLoader(ABC):
    """
    Abstract base class for document loaders.
    A loader is responsible for taking some raw input (e.g., a file path)
    and converting it into a standardized Document object.
    """

    @abstractmethod
    def load(self, source: Any, filename: str, doc_id: Optional[str] = None, **kwargs) -> Document:
        """
        Loads a document from the given source and returns a Document object.

        Args:
            source (Any): The source from which to load the document (e.g., file path, bytes, dictionary).
            filename (str): The original filename of the document.
            doc_id (Optional[str]): An optional unique identifier for the document. If not provided, a UUID will be generated.
            **kwargs: Additional parameters for loading.

        Returns:
            Document: The standardized Document object.
        """
        pass

class DocumentLoaderRegistry:
    """
    A registry to manage different document loaders.
    """
    _loaders: Dict[str, Type[BaseDocumentLoader]] = {}

    @classmethod
    def register_loader(cls, loader_type: str, loader_class: Type[BaseDocumentLoader]):
        """
        Registers a new document loader.

        Args:
            loader_type (str): A unique string identifier for the loader (e.g., "pdf", "html", "json_dict").
            loader_class (Type[BaseDocumentLoader]): The class of the loader to register.
        """
        if not issubclass(loader_class, BaseDocumentLoader):
            raise ValueError(f"Loader class must inherit from BaseDocumentLoader: {loader_class.__name__}")
        cls._loaders[loader_type] = loader_class

    @classmethod
    def get_loader(cls, loader_type: str) -> Type[BaseDocumentLoader]:
        """
        Retrieves a registered document loader by its type.

        Args:
            loader_type (str): The string identifier of the loader.

        Returns:
            Type[BaseDocumentLoader]: The class of the requested loader.

        Raises:
            ValueError: If no loader is registered for the given type.
        """
        loader = cls._loaders.get(loader_type)
        if not loader:
            raise ValueError(f"No document loader registered for type: {loader_type}")
        return loader

    @classmethod
    def list_loaders(cls) -> List[str]:
        """Lists all registered loader types."""
        return list(cls._loaders.keys())

class DictLoader(BaseDocumentLoader):
    """
    A loader that converts a dictionary (like the original 'document' input)
    into a Document object. It assumes the dictionary contains markdown content
    under 'md_di' or 'md_py' keys.
    """
    def load(self, source: Dict[str, Any], filename: str, doc_id: Optional[str] = None, **kwargs) -> Document:
        md_content = source.get("md_di") or source.get("md_py")
        if not md_content:
            raise ValueError("Dictionary source must contain 'md_di' or 'md_py' for text_content.")
        
        return Document(
            id=doc_id if doc_id else str(uuid.uuid4()), # Generate UUID if no doc_id
            filename=filename,
            text_content=md_content,
            raw_data=source # Store the original dict in raw_data for access to paragraphs etc.
        )

# Register the DictLoader
DocumentLoaderRegistry.register_loader("dict", DictLoader)
