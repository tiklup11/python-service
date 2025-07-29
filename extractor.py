import fitz  # PyMuPDF
import logging
import filetype
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
import re

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Document text extraction service using PyMuPDF (fitz)."""
    
    # Supported file extensions and their MIME types
    SUPPORTED_FORMATS = {
        'pdf': ['application/pdf'],
        'xps': ['application/vnd.ms-xpsdocument'],
        'epub': ['application/epub+zip'],
        'mobi': ['application/x-mobipocket-ebook'],
        'fb2': ['application/x-fictionbook+xml'],
        'cbz': ['application/vnd.comicbook+zip'],
    }
    
    def __init__(self):
        """Initialize the document extractor."""
        pass
        
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats."""
        return list(self.SUPPORTED_FORMATS.keys())
    
    def detect_file_format(self, file_content: bytes, filename: str) -> str:
        """Detect file format from content and filename."""
        try:
            # First try filetype detection by content
            kind = filetype.guess(file_content)
            if kind is not None:
                # Map MIME types to our format names
                for format_name, mime_types in self.SUPPORTED_FORMATS.items():
                    if kind.mime in mime_types:
                        return format_name
            
            # Fallback to file extension
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            if extension in self.SUPPORTED_FORMATS:
                return extension
                
            return 'unknown'
            
        except Exception as e:
            logger.warning(f"Format detection failed for {filename}: {e}")
            # Fallback to extension
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            return extension if extension in self.SUPPORTED_FORMATS else 'unknown'
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove null bytes and other problematic characters
        text = text.replace('\x00', '')
        text = text.replace('\x0c', '')  # form feed
        text = text.replace('\x0b', '')  # vertical tab
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        
        # Remove excessive whitespace while preserving structure
        lines = [line.strip() for line in text.split('\n')]
        clean_lines = [line for line in lines if line and self.is_printable_line(line)]
        
        # Join with spaces but preserve some structure
        result = ' '.join(clean_lines)
        
        # Final cleanup - normalize spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def is_printable_line(self, line: str) -> bool:
        """Check if a line contains mostly printable characters."""
        if not line:
            return False
        
        printable_count = sum(1 for char in line if char.isprintable() or char.isspace())
        ratio = printable_count / len(line)
        
        return ratio >= 0.7  # At least 70% printable characters
    
    def extract_text_from_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from a single document file."""
        result = {
            'filename': filename,
            'text': None,
            'error': None,
            'format': None,
            'pages': None,
            'file_size': len(file_content)
        }
        
        try:
            # Detect file format
            file_format = self.detect_file_format(file_content, filename)
            result['format'] = file_format
            
            if file_format == 'unknown':
                result['error'] = f"Unsupported file format for {filename}"
                return result
            
            # Open document with PyMuPDF
            doc = fitz.open(stream=file_content, filetype=file_format)
            result['pages'] = len(doc)
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)
            
            # Combine all text
            raw_text = '\n'.join(text_parts)
            
            # Clean and validate text
            cleaned_text = self.clean_text(raw_text)
            
            if not cleaned_text:
                result['error'] = "No readable text content found in document"
            else:
                result['text'] = cleaned_text
                logger.info(f"Successfully extracted {len(cleaned_text)} characters from {filename}")
            
            doc.close()
            
        except Exception as e:
            error_msg = f"Text extraction failed for {filename}: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
        
        return result
    
    def process_multiple_files(self, files: List[Tuple[bytes, str]]) -> Dict[str, Any]:
        """Process multiple document files and extract text from each."""
        documents = []
        summary = {
            'total': len(files),
            'successful': 0,
            'failed': 0,
            'formats_processed': {}
        }
        
        for file_content, filename in files:
            logger.info(f"Processing file: {filename}")
            
            result = self.extract_text_from_file(file_content, filename)
            documents.append(result)
            
            # Update summary
            if result['error'] is None:
                summary['successful'] += 1
            else:
                summary['failed'] += 1
            
            # Track formats
            file_format = result['format'] or 'unknown'
            summary['formats_processed'][file_format] = summary['formats_processed'].get(file_format, 0) + 1
        
        logger.info(f"Batch processing complete: {summary['successful']}/{summary['total']} successful")
        
        return {
            'success': summary['failed'] == 0,  # Success if no failures
            'documents': documents,
            'summary': summary
        }