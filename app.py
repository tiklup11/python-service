import logging
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Load environment variables first
import dotenv
dotenv.load_dotenv()

from models import ExtractionResponse, HealthResponse, ErrorResponse, ExtractedDocument, ExtractionSummary
from extractor import DocumentExtractor
from websocket_handlers import websocket_handler
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Document Text Extractor & Gemini Audio API",
    description="Microservice for extracting text from documents and real-time audio conversation with Gemini",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins + ["*"],  # Include configured origins
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


@app.get("/gemini/health")
async def gemini_health_check():
    """Gemini service health check"""
    try:
        return {
            "status": "healthy",
            "gemini_model": settings.gemini.model,
            "voice_name": settings.gemini.voice_name,
            "timestamp": extractor.get_supported_formats()  # Reuse timestamp logic
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini service unavailable: {str(e)}"
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


@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Gemini audio streaming"""
    await websocket_handler.handle_connection(websocket)


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
    import dotenv
    dotenv.load_dotenv()
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger.info(f"Starting Document Text Extractor & Gemini Audio service on {settings.server.host}:{settings.server.port}")
    logger.info(f"Supported document formats: {extractor.get_supported_formats()}")
    logger.info(f"Gemini model: {settings.gemini.model}")
    
    uvicorn.run(
        "app:app",
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level.lower(),
        reload=settings.server.reload,
        log_config=log_config
    )