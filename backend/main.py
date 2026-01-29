"""
Practical Review API - Document correction service
"""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
import uvicorn

from document_processor import DocumentProcessor
from ai_corrector import AICorrector

app = FastAPI(
    title="Practical Review API",
    description="AI-powered document correction",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

doc_processor = DocumentProcessor()
ai_corrector = AICorrector()

SUPPORTED_FORMATS = {'.pdf', '.xlsx', '.docx', '.txt'}


@app.get("/")
async def root():
    return {"message": "Practical Review API", "status": "running"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ai_available": ai_corrector.is_available(),
        "ai_provider": ai_corrector.get_provider()
    }


@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """Extract text from a document (used for meta review)."""
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"Unsupported format. Use: {', '.join(SUPPORTED_FORMATS)}")
    
    try:
        content = await file.read()
        extracted = doc_processor.extract_text(content, file_ext)
        
        return JSONResponse({
            "text": extracted.get('text', ''),
            "filename": file.filename
        })
        
    except Exception as e:
        raise HTTPException(500, f"Extraction error: {str(e)}")


@app.post("/upload")
async def upload_and_correct(
    file: UploadFile = File(...),
    meta_review: str = Form(None)
):
    """Upload a document, correct it, and return the corrected version."""
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"Unsupported format. Use: {', '.join(SUPPORTED_FORMATS)}")
    
    try:
        content = await file.read()
        extracted = doc_processor.extract_text(content, file_ext)
        
        if not extracted['text'].strip():
            raise HTTPException(400, "No text found in document")
        
        corrected = await ai_corrector.correct_text(extracted, meta_review=meta_review)
        corrected_file = doc_processor.rebuild_document(corrected, file_ext, content)
        
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"corrected_{file.filename}")
        
        with open(output_path, 'wb') as f:
            f.write(corrected_file)
        
        media_types = {
            '.pdf': 'application/pdf',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain'
        }
        
        return FileResponse(
            path=output_path,
            filename=f"corrected_{file.filename}",
            media_type=media_types.get(file_ext, 'application/octet-stream')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/preview")
async def preview_corrections(
    file: UploadFile = File(...),
    meta_review: str = Form(None)
):
    """Preview corrections without downloading."""
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"Unsupported format. Use: {', '.join(SUPPORTED_FORMATS)}")
    
    try:
        content = await file.read()
        extracted = doc_processor.extract_text(content, file_ext)
        
        if not extracted['text'].strip():
            raise HTTPException(400, "No text found in document")
        
        corrected = await ai_corrector.correct_text(extracted, meta_review=meta_review)
        
        return JSONResponse({
            "original": extracted['text'],
            "corrected": corrected.get('text', ''),
            "changes": corrected.get('changes', []),
            "summary": corrected.get('summary', '')
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/convert")
async def convert_format(
    text: str = Form(...),
    format: str = Form(...),
    original_name: str = Form("document")
):
    """Convert corrected text to a specific format."""
    if format not in ['pdf', 'docx', 'txt', 'xlsx']:
        raise HTTPException(400, f"Unsupported format: {format}")
    
    try:
        corrected_data = {'text': text}
        
        # For conversion, we don't have the original file, so create from scratch
        if format == 'txt':
            content = text.encode('utf-8')
            media_type = 'text/plain'
        elif format == 'pdf':
            content = doc_processor.rebuild_document(corrected_data, '.pdf', None)
            media_type = 'application/pdf'
        elif format == 'docx':
            # Create a new DOCX from scratch
            from docx import Document
            import io
            doc = Document()
            for para in text.split('\n'):
                if para.strip():
                    doc.add_paragraph(para)
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            content = buffer.getvalue()
            media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif format == 'xlsx':
            # Create a new XLSX from scratch
            from openpyxl import Workbook
            import io
            wb = Workbook()
            ws = wb.active
            ws.title = "Corrected Text"
            for i, line in enumerate(text.split('\n'), 1):
                ws.cell(row=i, column=1, value=line)
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            content = buffer.getvalue()
            media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return Response(content=content, media_type=media_type)
        
    except Exception as e:
        raise HTTPException(500, f"Conversion error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
