import os
import json
import logging
import base64
from flask import jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None
    ExifTags = None
    logger.warning("Pillow not installed. Image preview features will be limited. Install with: pip install Pillow")

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logger.warning("PyPDF2 not installed. PDF preview features will be limited. Install with: pip install PyPDF2")

try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None
    logger.warning("PyMuPDF (fitz) not installed. PyMuPDF PDF parser will not be available. Install with: pip install pymupdf")

try:
    from langdetect import detect, LangDetectException
except ImportError:
    detect = None
    LangDetectException = None
    logger.warning("langdetect not installed. Language detection for PDFs will not be available. Install with: pip install langdetect")

try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None
    logger.warning("pymupdf4llm not installed. pymupdf4llm PDF parser will not be available. Install with: pip install pymupdf4llm")

# File type mapping
FILE_TYPE_ICONS = {
    # Data files
    '.json': 'bi-filetype-json',
    '.csv': 'bi-file-earmark-bar-graph',
    '.parquet': 'bi-file-earmark-arrow',
    '.xlsx': 'bi-file-earmark-spreadsheet',
    '.xls': 'bi-file-earmark-spreadsheet',
    
    # Text files
    '.txt': 'bi-file-earmark-text',
    '.md': 'bi-file-earmark-text',
    '.log': 'bi-file-earmark-text',
    '.html': 'bi-filetype-html', # Added for HTML preview
    '.xml': 'bi-filetype-xml', # Added for XML preview
    
    # Code files
    '.py': 'bi-file-earmark-code',
    '.js': 'bi-file-earmark-code',
    '.css': 'bi-file-earmark-code',
    '.sql': 'bi-file-earmark-code',
    
    # Image files
    '.jpg': 'bi-file-earmark-image',
    '.jpeg': 'bi-file-earmark-image',
    '.png': 'bi-file-earmark-image',
    '.gif': 'bi-file-earmark-image',
    '.bmp': 'bi-file-earmark-image',
    '.tiff': 'bi-file-earmark-image',

    # PDF files
    '.pdf': 'bi-filetype-pdf',
    
    # Binary files
    '.bin': 'bi-file-earmark-binary',
    '.exe': 'bi-file-earmark-binary',
    '.dll': 'bi-file-earmark-binary',
}

CONTENT_TYPE_MAPPING = {
    'application/json': 'bi-filetype-json',
    'text/csv': 'bi-file-earmark-bar-graph',
    'application/vnd.ms-excel': 'bi-file-earmark-spreadsheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'bi-file-earmark-spreadsheet',
    'text/plain': 'bi-file-earmark-text',
    'image/jpeg': 'bi-file-earmark-image',
    'image/png': 'bi-file-earmark-image',
    'image/gif': 'bi-file-earmark-image',
    'image/bmp': 'bi-file-earmark-image',
    'application/pdf': 'bi-filetype-pdf',
    'text/html': 'bi-filetype-html',
    'application/xml': 'bi-filetype-xml',
    'text/xml': 'bi-filetype-xml',
    'application/octet-stream': 'bi-file-earmark-binary',
}

PREVIEWABLE_EXTENSIONS = [
    '.json', '.csv', '.parquet', # Already supported data files
    '.txt', '.log', '.md', '.html', '.xml', # Text-based files
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', # Image files
    '.pdf' # PDF files
]

def get_file_icon(filename, content_type=None):
    """Get appropriate icon class based on file extension and content type"""
    _, ext = os.path.splitext(filename.lower())
    
    # Check by extension
    if ext in FILE_TYPE_ICONS:
        return FILE_TYPE_ICONS[ext]
    
    # Check by content type
    if content_type and content_type in CONTENT_TYPE_MAPPING:
        return CONTENT_TYPE_MAPPING[content_type]
    
    # Default by content type category
    if content_type:
        if content_type.startswith('text/'):
            return 'bi-file-earmark-text'
        elif content_type.startswith('image/'):
            return 'bi-file-earmark-image'
        elif content_type.startswith('application/pdf'):
            return 'bi-filetype-pdf'
        elif content_type.startswith('application/'):
            return 'bi-file-earmark-code'
    
    return 'bi-file-earmark'

def is_previewable(filename, content_type=None):
    """Check if a file is previewable based on extension and content type"""
    _, ext = os.path.splitext(filename.lower())
    return ext in PREVIEWABLE_EXTENSIONS

def format_size(size_in_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def process_file_metadata(blob):
    """Process and add file metadata for UI display"""
    display_name = blob.get('display_name', '')
    content_type = blob.get('content_type', '')
    
    # Add icon class based on file type
    blob['icon_class'] = get_file_icon(display_name, content_type)
    
    # Add flag if file is previewable
    blob['is_previewable'] = is_previewable(display_name, content_type)
    
    # Detect file type from extension
    _, ext = os.path.splitext(display_name.lower())
    blob['file_type'] = ext[1:] if ext else ''

def preview_data_file(file_path, file_type, page=1, rows_per_page=100, pdf_parser='pypdf2'):
    """Preview data files (JSON, CSV, Parquet) and other previewable types"""
    file_size = os.path.getsize(file_path)
    formatted_size = format_size(file_size)
    
    try:
        if file_type == 'json':
            return preview_json(file_path, formatted_size)
        elif file_type == 'csv':
            return preview_csv(file_path, formatted_size, page, rows_per_page)
        elif file_type == 'parquet':
            return preview_parquet(file_path, formatted_size, page, rows_per_page)
        elif file_type in ['txt', 'log', 'md', 'html', 'xml']:
            return preview_text(file_path, formatted_size)
        elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            return preview_image(file_path, formatted_size)
        elif file_type == 'pdf':
            return preview_pdf_text(file_path, formatted_size, pdf_parser)
        else:
            return jsonify({'error': f'Unsupported file type: {file_type}'}), 400
    except Exception as e:
        logger.error(f"Error previewing {file_type} file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 400

def preview_json(file_path, formatted_size):
    """Preview JSON file"""
    try:
        file_size = os.path.getsize(file_path)
        is_large = file_size > 5 * 1024 * 1024  # 5MB threshold
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Limit data size for very large JSON
        if is_large and isinstance(data, list) and len(data) > 100:
            data = data[:100]
        
        return jsonify({
            'data': data,
            'metadata': {
                'size': formatted_size,
                'truncated': is_large,
                'type': 'json'
            }
        })
    
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error previewing JSON: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error processing JSON: {str(e)}'}), 400

def preview_csv(file_path, formatted_size, page=1, rows_per_page=100):
    """Preview CSV file"""
    try:
        try:
            # Try using pandas if available
            import pandas as pd
            
            # Count total rows
            # Using iterator to avoid loading entire file into memory for large files
            with open(file_path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header row
            
            # Skip rows based on pagination
            skip_rows = (page - 1) * rows_per_page if page > 1 else None
            
            # Read the page data
            df = pd.read_csv(file_path, skiprows=skip_rows, nrows=rows_per_page, encoding='utf-8')
            
            # Replace NaN with None for valid JSON conversion
            df = df.where(pd.notna(df), None)
            
            records = df.to_dict('records')
            columns = df.columns.tolist()
            
        except ImportError:
            # Fallback to manual CSV reading
            import csv
            
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                
                # Read header
                headers = next(csv_reader)
                
                # Count total rows
                # Need to reset file pointer or reopen to count rows from beginning
                f.seek(0)
                total_rows = sum(1 for _ in csv_reader) -1 # Subtract header row
                
                # Reset and skip to page start
                f.seek(0)
                next(csv_reader) # Skip header again
                
                # Skip rows for pagination
                start_row = (page - 1) * rows_per_page
                for _ in range(start_row):
                    try:
                        next(csv_reader)
                    except StopIteration:
                        break
                
                # Read page rows
                records = []
                for _ in range(rows_per_page):
                    try:
                        row = next(csv_reader)
                        records.append(dict(zip(headers, row)))
                    except StopIteration:
                        break
                
                columns = headers
        
        # Calculate pagination data
        total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
        
        return jsonify({
            'data': records,
            'metadata': {
                'size': formatted_size,
                'totalRows': total_rows,
                'currentPage': page,
                'totalPages': total_pages,
                'rowsPerPage': rows_per_page,
                'columns': columns,
                'type': 'csv'
            }
        })
        
    except Exception as e:
        logger.error(f"CSV preview error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error processing CSV: {str(e)}'}), 400

def preview_parquet(file_path, formatted_size, page=1, rows_per_page=100):
    """Preview Parquet file"""
    try:
        try:
            import pyarrow.parquet as pq
            import pandas as pd
            
            # Open and read parquet metadata
            parquet_file = pq.ParquetFile(file_path)
            total_rows = parquet_file.metadata.num_rows
            
            # Calculate pagination
            start_row = (page - 1) * rows_per_page
            
            # Read the requested page of data
            # Optimized to read only relevant row groups if possible, but pandas.read_parquet handles it
            df = pd.read_parquet(file_path, engine='pyarrow')
            
            # Replace NaN with None for valid JSON conversion
            df = df.where(pd.notna(df), None)
            
            # Get page slice
            page_df = df.iloc[start_row:start_row+rows_per_page]
            records = page_df.to_dict('records')
            columns = page_df.columns.tolist()
            
            # Get schema information
            schema_fields = []
            for i, col in enumerate(df.columns):
                dtype = str(df[col].dtype)
                schema_fields.append({'name': col, 'type': dtype})
            
            # Calculate pagination metadata
            total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
            
            return jsonify({
                'data': records,
                'metadata': {
                    'size': formatted_size,
                    'totalRows': total_rows,
                    'currentPage': page,
                    'totalPages': total_pages,
                    'rowsPerPage': rows_per_page,
                    'columns': columns,
                    'schema': schema_fields,
                    'type': 'parquet'
                }
            })
            
        except ImportError:
            return jsonify({
                'error': 'Parquet support requires pyarrow and pandas libraries. Install with: pip install pyarrow pandas'
            }), 500
            
    except Exception as e:
        logger.error(f"Parquet preview error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error processing Parquet file: {str(e)}'}), 400

def preview_text(file_path, formatted_size):
    """Preview text-based file (TXT, LOG, MD, HTML, XML)"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1024 * 1024) # Read up to 1MB of text
        
        truncated = len(content) == (1024 * 1024)
        
        return jsonify({
            'data': content,
            'metadata': {
                'size': formatted_size,
                'truncated': truncated,
                'type': 'text'
            }
        })
    except Exception as e:
        logger.error(f"Error previewing text file: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error processing text file: {str(e)}'}), 400

def preview_image(file_path, formatted_size):
    """Preview image file (JPG, PNG, GIF, BMP, TIFF)"""
    if not Image:
        return jsonify({'error': 'Pillow library not installed for image preview.'}), 500

    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        image_metadata = {}
        try:
            img = Image.open(file_path)
            # Extract EXIF data
            if hasattr(img, '_getexif') and img._getexif():
                exif = {
                    ExifTags.TAGS[k]: v
                    for k, v in img._getexif().items()
                    if k in ExifTags.TAGS
                }
                image_metadata['exif'] = exif
            
            image_metadata['format'] = img.format
            image_metadata['mode'] = img.mode
            image_metadata['size'] = img.size # (width, height)
        except Exception as e:
            logger.warning(f"Could not extract image metadata for {file_path}: {str(e)}")
        
        return jsonify({
            'data': f"data:image/{os.path.splitext(file_path)[1][1:]};base64,{encoded_string}",
            'metadata': {
                'size': formatted_size,
                'type': 'image',
                'image_info': image_metadata
            }
        })
    except Exception as e:
        logger.error(f"Error previewing image file: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error processing image file: {str(e)}'}), 400

def preview_pdf_text(file_path, formatted_size, pdf_parser='pypdf2'):
    """Extract text from PDF file using the specified parser and format as Markdown,
    and include detailed PDF metadata.
    """
    
    pdf_content_markdown = []
    total_pages = 0
    truncated = False
    pdf_metadata = {}

    if pdf_parser == 'pymupdf':
        if not fitz:
            return jsonify({'error': 'PyMuPDF (fitz) library not installed for PDF preview.'}), 500
        try:
            doc = fitz.open(file_path)
            total_pages = doc.page_count
            pdf_metadata = doc.metadata or {} # Get PDF metadata

            # Extract text from the first few pages for language detection
            sample_text = ""
            for i in range(min(total_pages, 3)): # Use first 3 pages for language detection
                page = doc.load_page(i)
                sample_text += page.get_text("text") + " "
            
            if detect and sample_text.strip():
                try:
                    detected_language = detect(sample_text)
                    pdf_metadata['language'] = detected_language
                except LangDetectException:
                    logger.warning(f"Could not detect language for PDF: {file_path}")
                    pdf_metadata['language'] = 'unknown'
                except Exception as e:
                    logger.warning(f"An unexpected error occurred during language detection for PDF: {file_path} - {e}")
                    pdf_metadata['language'] = 'error'

            for i in range(min(total_pages, 5)): # Preview first 5 pages or fewer
                page = doc.load_page(i)
                text = page.get_text("text")
                pdf_content_markdown.append(f"## Page {i + 1}\n\n```text\n{text.strip()}\n```")
            doc.close()
            truncated = total_pages > 5
        except Exception as e:
            logger.error(f"Error processing PDF with PyMuPDF: {str(e)}", exc_info=True)
            return jsonify({'error': f'Error processing PDF with PyMuPDF: {str(e)}'}), 400
    elif pdf_parser == 'pypdf2':
        if not PyPDF2:
            return jsonify({'error': 'PyPDF2 library not installed for PDF preview.'}), 500
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                pdf_metadata = reader.metadata or {} # Get PDF metadata
                # PyPDF2 metadata keys are different, convert to a more generic dict
                # Example: {'/Author': '...', '/Title': '...'} -> {'author': '...', 'title': '...'}
                pdf_metadata = {key.replace('/', '').lower(): value for key, value in pdf_metadata.items()}
                
                # Extract text from the first few pages for language detection
                sample_text = ""
                for i in range(min(total_pages, 3)): # Use first 3 pages for language detection
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text:
                        sample_text += text + " "
                
                if detect and sample_text.strip():
                    try:
                        detected_language = detect(sample_text)
                        pdf_metadata['language'] = detected_language
                    except LangDetectException:
                        logger.warning(f"Could not detect language for PDF: {file_path}")
                        pdf_metadata['language'] = 'unknown'
                    except Exception as e:
                        logger.warning(f"An unexpected error occurred during language detection for PDF: {file_path} - {e}")
                        pdf_metadata['language'] = 'error'

                for i in range(min(total_pages, 5)): # Preview first 5 pages or fewer
                    page = reader.pages[i]
                    text = page.extract_text()
                    pdf_content_markdown.append(f"## Page {i + 1}\n\n```text\n{text.strip()}\n```")
            truncated = total_pages > 5
        except Exception as e:
            logger.error(f"Error processing PDF with PyPDF2: {str(e)}", exc_info=True)
            return jsonify({'error': f'Error processing PDF with PyPDF2: {str(e)}'}), 400
    elif pdf_parser == 'pymupdf4llm':
        if not pymupdf4llm:
            return jsonify({'error': 'pymupdf4llm library not installed for PDF preview.'}), 500
        try:
            doc = fitz.open(file_path)
            total_pages = doc.page_count
            pdf_metadata = doc.metadata or {}
            doc.close()

            md_text = pymupdf4llm.to_markdown(file_path)
            
            return jsonify({
                'data': md_text,
                'metadata': {
                    'size': formatted_size,
                    'total_pages': total_pages,
                    'truncated': False,
                    'type': 'pdf_markdown',
                    'pdf_metadata': pdf_metadata
                }
            })
        except Exception as e:
            logger.error(f"Error processing PDF with pymupdf4llm: {str(e)}", exc_info=True)
            return jsonify({'error': f'Error processing PDF with pymupdf4llm: {str(e)}'}), 400
    else:
        return jsonify({'error': f'Invalid PDF parser specified: {pdf_parser}'}), 400

    return jsonify({
        'data': "\n\n---\n\n".join(pdf_content_markdown), # Join pages with a Markdown separator
        'metadata': {
            'size': formatted_size,
            'total_pages': total_pages,
            'truncated': truncated,
            'type': 'pdf_markdown', # Indicate that the content is Markdown
            'pdf_metadata': pdf_metadata # Include detailed PDF metadata
        }
    })