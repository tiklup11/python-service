import logging
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from models import ExtractionResponse, HealthResponse, ErrorResponse, ExtractedDocument, ExtractionSummary
from extractor import DocumentExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Document Text Extractor",
    description="Microservice for extracting text from various document formats using PyMuPDF",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize document extractor
extractor = DocumentExtractor()

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
MAX_FILES = 50  # Maximum number of files per request


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        supported_formats=extractor.get_supported_formats()
    )


@app.post("/extract-text", response_model=ExtractionResponse)
async def extract_text(files: List[UploadFile] = File(...)):
    """
    Extract text from multiple document files.
    
    Supports various document formats including PDF, XPS, EPUB, etc.
    """
    logger.info(f"Received request to process {len(files)} files")
    
    # Validate request
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_FILES} files allowed per request"
        )
    
    try:
        # Process files
        file_data = []
        
        for file in files:
            # Validate file size
            file_content = await file.read()
            if len(file_content) > MAX_FILE_SIZE:
                logger.warning(f"File {file.filename} exceeds size limit")
                continue
            
            if len(file_content) == 0:
                logger.warning(f"File {file.filename} is empty")
                continue
            
            file_data.append((file_content, file.filename))
        
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files to process"
            )
        
        # Extract text using PyMuPDF
        result = extractor.process_multiple_files(file_data)
        
        # Convert to response model
        documents = [ExtractedDocument(**doc) for doc in result['documents']]
        summary = ExtractionSummary(**result['summary'])
        
        response = ExtractionResponse(
            success=result['success'],
            documents=documents,
            summary=summary
        )
        
        logger.info(f"Successfully processed {summary.successful}/{summary.total} files")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during text extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(e)}"
        )


@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported document formats."""
    return {
        "formats": extractor.get_supported_formats(),
        "details": {
            "pdf": "Portable Document Format",
            "xps": "XML Paper Specification",
            "epub": "Electronic Publication",
            "mobi": "Mobipocket eBook",
            "fb2": "FictionBook",
            "cbz": "Comic Book Archive"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            code="INTERNAL_ERROR"
        ).dict()
    )


if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger.info(f"Starting Document Text Extractor service on {host}:{port}")
    logger.info(f"Supported formats: {extractor.get_supported_formats()}")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        log_config=log_config
    )