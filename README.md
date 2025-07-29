# Document Text Extractor Microservice

A Python-based microservice for extracting text from various document formats using PyMuPDF.

## Features

- **Multi-format Support**: PDF, XPS, EPUB, MOBI, FB2, CBZ
- **Batch Processing**: Process multiple files in a single request
- **High Performance**: Built with FastAPI and PyMuPDF
- **Error Handling**: Comprehensive error reporting per file
- **Docker Ready**: Containerized for easy deployment

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| PDF | `.pdf` | Portable Document Format |
| XPS | `.xps` | XML Paper Specification |
| EPUB | `.epub` | Electronic Publication |
| MOBI | `.mobi` | Mobipocket eBook |
| FB2 | `.fb2` | FictionBook |
| CBZ | `.cbz` | Comic Book Archive |

## API Endpoints

### POST /extract-text
Extract text from multiple document files.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `files` (multiple files)

**Response:**
```json
{
  "success": true,
  "documents": [
    {
      "filename": "document.pdf",
      "text": "Extracted text content...",
      "error": null,
      "format": "pdf",
      "pages": 5,
      "file_size": 1024000
    }
  ],
  "summary": {
    "total": 1,
    "successful": 1,
    "failed": 0,
    "formats_processed": {"pdf": 1}
  }
}
```

### GET /health
Health check endpoint.

### GET /supported-formats
List of supported document formats.

## Local Development

### Prerequisites
- Python 3.11+
- pip

### Setup
```bash
cd python-microservice
pip install -r requirements.txt
python app.py
```

The service will be available at `http://localhost:8001`

## Docker Deployment

### Build Image
```bash
docker build -t document-extractor .
```

### Run Container
```bash
docker run -p 8001:8001 document-extractor
```

## Configuration

Environment variables:
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8001)
- `LOG_LEVEL`: Logging level (default: info)
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 50MB)
- `MAX_FILES`: Maximum files per request (default: 50)

## Integration with Go Service

The microservice is designed to be called from the Go backend:

```go
// Example Go client code
resp, err := http.Post("http://python-extractor:8001/extract-text", "multipart/form-data", body)
```

## Performance Considerations

- Files are processed sequentially to manage memory usage
- Large files (>50MB) are rejected to prevent timeouts
- Text is cleaned and validated before returning
- Comprehensive logging for monitoring and debugging

## Error Handling

The service provides detailed error information:
- File-level errors (per document)
- Format detection failures
- Text extraction failures
- File size/count limit violations