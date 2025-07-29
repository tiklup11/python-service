from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ExtractedDocument(BaseModel):
    filename: str = Field(..., description="Original filename of the document")
    text: Optional[str] = Field(None, description="Extracted text content")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    format: Optional[str] = Field(None, description="Document format/type")
    pages: Optional[int] = Field(None, description="Number of pages in document")
    file_size: Optional[int] = Field(None, description="File size in bytes")


class ExtractionSummary(BaseModel):
    total: int = Field(..., description="Total number of files processed")
    successful: int = Field(..., description="Number of successfully processed files")
    failed: int = Field(..., description="Number of failed extractions")
    formats_processed: Dict[str, int] = Field(default_factory=dict, description="Count by file format")


class ExtractionResponse(BaseModel):
    success: bool = Field(..., description="Overall operation success status")
    documents: List[ExtractedDocument] = Field(..., description="List of processed documents")
    summary: ExtractionSummary = Field(..., description="Processing summary")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Service version")
    supported_formats: List[str] = Field(..., description="Supported document formats")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")