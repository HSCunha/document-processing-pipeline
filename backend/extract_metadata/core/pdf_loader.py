from typing import Any, Optional
import uuid
import fitz
import pymupdf4llm
from extract_metadata.core.loaders import BaseDocumentLoader, DocumentLoaderRegistry
from extract_metadata.core.schema import Document

class PdfLoader(BaseDocumentLoader):
    """
    A loader that extracts markdown content from a PDF file using pymupdf4llm.
    """
    def load(self, source: Any, filename: str, doc_id: Optional[str] = None, **kwargs) -> Document:
        """
        Loads a document from the given PDF file path and returns a Document object.

        Args:
            source (Any): The file path of the PDF document.
            filename (str): The original filename of the document.
            doc_id (Optional[str]): An optional unique identifier for the document.
            **kwargs: Additional parameters for loading.

        Returns:
            Document: The standardized Document object with markdown content.
        """
        md_content = pymupdf4llm.to_markdown(source)
        
        return Document(
            id=doc_id if doc_id else str(uuid.uuid4()),
            filename=filename,
            text_content=md_content
        )

# Register the PdfLoader
DocumentLoaderRegistry.register_loader("pdf", PdfLoader)
