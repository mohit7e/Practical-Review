"""
Document Correction API
Handles PDF, XLSX, DOCX files - extracts text, corrects it, and returns in original format.
"""

import os
import io
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from document_processor import DocumentProcessor
from ai_corrector import AICorrector

app = FastAPI(
    title="Document Correction API",
    description="AI-powered document correction for spelling, grammar, and factual accuracy",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors
doc_processor = DocumentProcessor()
ai_corrector = AICorrector()

SUPPORTED_FORMATS = {'.pdf', '.xlsx', '.docx', '.txt'}


@app.get("/")
async def root():
    return {"message": "Document Correction API", "status": "running"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "ai_available": ai_corrector.is_available(),
        "ai_provider": ai_corrector.get_provider()
    }


@app.post("/upload")
async def upload_and_correct(file: UploadFile = File(...)):
    """
    Upload a document, correct it, and return the corrected version.
    Supports: PDF, XLSX, DOCX, TXT
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Extract text from document
        extracted_data = doc_processor.extract_text(content, file_ext)
        
        if not extracted_data['text'].strip():
            raise HTTPException(status_code=400, detail="No text content found in the document")
        
        # Correct the text using AI
        corrected_data = await ai_corrector.correct_text(extracted_data)
        
        # Rebuild document in original format
        corrected_file = doc_processor.rebuild_document(
            corrected_data,
            file_ext,
            original_content=content
        )
        
        # Create temp file for response
        temp_dir = tempfile.mkdtemp()
        output_filename = f"corrected_{file.filename}"
        output_path = os.path.join(temp_dir, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(corrected_file)
        
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type=_get_media_type(file_ext),
            headers={
                "X-Original-Text": str(len(extracted_data['text'])),
                "X-Corrected-Text": str(len(corrected_data.get('text', '')))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/preview")
async def preview_corrections(file: UploadFile = File(...)):
    """
    Preview corrections without downloading - returns diff/comparison.
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    try:
        content = await file.read()
        extracted_data = doc_processor.extract_text(content, file_ext)
        
        if not extracted_data['text'].strip():
            raise HTTPException(status_code=400, detail="No text content found in the document")
        
        corrected_data = await ai_corrector.correct_text(extracted_data)
        
        return JSONResponse({
            "original": extracted_data['text'],
            "corrected": corrected_data.get('text', ''),
            "changes": corrected_data.get('changes', []),
            "summary": corrected_data.get('summary', '')
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


def _get_media_type(ext: str) -> str:
    """Get MIME type for file extension."""
    types = {
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain'
    }
    return types.get(ext, 'application/octet-stream')


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

