"""
Document Processor - Handles extraction and rebuilding of various document formats.
Supports: PDF, XLSX, DOCX, TXT
"""

import io
from typing import Dict, Any, List
from dataclasses import dataclass

# PDF handling
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# XLSX handling
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter

# DOCX handling
from docx import Document
from docx.shared import Pt


class DocumentProcessor:
    """Handles document text extraction and rebuilding."""
    
    def extract_text(self, content: bytes, file_ext: str) -> Dict[str, Any]:
        """
        Extract text from document based on file type.
        Returns structured data with text and metadata.
        """
        extractors = {
            '.pdf': self._extract_pdf,
            '.xlsx': self._extract_xlsx,
            '.docx': self._extract_docx,
            '.txt': self._extract_txt,
        }
        
        extractor = extractors.get(file_ext)
        if not extractor:
            raise ValueError(f"Unsupported format: {file_ext}")
        
        return extractor(content)
    
    def rebuild_document(self, corrected_data: Dict[str, Any], file_ext: str, 
                         original_content: bytes = None) -> bytes:
        """
        Rebuild document with corrected text in original format.
        """
        builders = {
            '.pdf': self._build_pdf,
            '.xlsx': self._build_xlsx,
            '.docx': self._build_docx,
            '.txt': self._build_txt,
        }
        
        builder = builders.get(file_ext)
        if not builder:
            raise ValueError(f"Unsupported format: {file_ext}")
        
        return builder(corrected_data, original_content)
    
    # ===================== EXTRACTORS =====================
    
    def _extract_pdf(self, content: bytes) -> Dict[str, Any]:
        """Extract text from PDF preserving page structure."""
        pages = []
        full_text = []
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({
                    'page_num': i + 1,
                    'text': text,
                    'width': page.width,
                    'height': page.height
                })
                full_text.append(text)
        
        return {
            'type': 'pdf',
            'text': '\n\n'.join(full_text),
            'pages': pages,
            'page_count': len(pages)
        }
    
    def _extract_xlsx(self, content: bytes) -> Dict[str, Any]:
        """Extract text from Excel preserving sheet/cell structure."""
        wb = load_workbook(io.BytesIO(content))
        sheets = []
        full_text = []
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            cells = []
            sheet_text = []
            
            for row in ws.iter_rows():
                row_data = []
                for cell in row:
                    if cell.value is not None:
                        cell_value = str(cell.value)
                        row_data.append({
                            'row': cell.row,
                            'col': cell.column,
                            'value': cell_value
                        })
                        sheet_text.append(cell_value)
                if row_data:
                    cells.extend(row_data)
            
            sheets.append({
                'name': sheet_name,
                'cells': cells,
                'text': ' '.join(sheet_text)
            })
            full_text.extend(sheet_text)
        
        wb.close()
        
        return {
            'type': 'xlsx',
            'text': ' '.join(full_text),
            'sheets': sheets,
            'sheet_count': len(sheets)
        }
    
    def _extract_docx(self, content: bytes) -> Dict[str, Any]:
        """Extract text from Word document preserving paragraph structure."""
        doc = Document(io.BytesIO(content))
        paragraphs = []
        full_text = []
        
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                paragraphs.append({
                    'index': i,
                    'text': para.text,
                    'style': para.style.name if para.style else 'Normal'
                })
                full_text.append(para.text)
        
        # Also extract text from tables
        tables = []
        for t_idx, table in enumerate(doc.tables):
            table_data = []
            for r_idx, row in enumerate(table.rows):
                row_data = []
                for c_idx, cell in enumerate(row.cells):
                    if cell.text.strip():
                        row_data.append({
                            'row': r_idx,
                            'col': c_idx,
                            'text': cell.text
                        })
                        full_text.append(cell.text)
                if row_data:
                    table_data.append(row_data)
            if table_data:
                tables.append({'index': t_idx, 'rows': table_data})
        
        return {
            'type': 'docx',
            'text': '\n'.join(full_text),
            'paragraphs': paragraphs,
            'tables': tables,
            'paragraph_count': len(paragraphs)
        }
    
    def _extract_txt(self, content: bytes) -> Dict[str, Any]:
        """Extract text from plain text file."""
        text = content.decode('utf-8', errors='replace')
        lines = text.split('\n')
        
        return {
            'type': 'txt',
            'text': text,
            'lines': lines,
            'line_count': len(lines)
        }
    
    # ===================== BUILDERS =====================
    
    def _build_pdf(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build a new PDF with corrected text."""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Create custom style
        custom_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=12
        )
        
        # Split corrected text into paragraphs
        text = corrected_data.get('text', '')
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            if para.strip():
                # Escape special characters for ReportLab
                safe_para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(safe_para, custom_style))
                story.append(Spacer(1, 6))
        
        if story:
            doc.build(story)
        else:
            # Empty document fallback
            doc.build([Paragraph("No content", styles['Normal'])])
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_xlsx(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build Excel file with corrected text in cells."""
        # Load original to preserve structure
        original_wb = load_workbook(io.BytesIO(original))
        
        # Parse corrected text back to cells
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        sheets = original_data.get('sheets', [])
        
        # Create mapping of original text to corrected text
        corrections = self._create_correction_map(
            original_data.get('original_text', ''),
            corrected_text
        )
        
        # Apply corrections to cells
        for sheet_info in sheets:
            sheet_name = sheet_info.get('name')
            if sheet_name in original_wb.sheetnames:
                ws = original_wb[sheet_name]
                for cell_info in sheet_info.get('cells', []):
                    row, col = cell_info['row'], cell_info['col']
                    original_value = cell_info['value']
                    
                    # Find corrected value
                    corrected_value = corrections.get(original_value, original_value)
                    ws.cell(row=row, column=col, value=corrected_value)
        
        buffer = io.BytesIO()
        original_wb.save(buffer)
        original_wb.close()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_docx(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build Word document with corrected text."""
        # Load original to preserve formatting
        doc = Document(io.BytesIO(original))
        
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        paragraphs = original_data.get('paragraphs', [])
        
        # Create correction map
        corrections = self._create_correction_map(
            original_data.get('original_text', ''),
            corrected_text
        )
        
        # Apply corrections to paragraphs
        for para_info in paragraphs:
            idx = para_info.get('index', 0)
            if idx < len(doc.paragraphs):
                original_text = para_info.get('text', '')
                corrected = corrections.get(original_text, original_text)
                
                # Preserve runs/formatting by updating text
                para = doc.paragraphs[idx]
                if para.runs:
                    # Try to preserve formatting by updating first run
                    para.runs[0].text = corrected
                    for run in para.runs[1:]:
                        run.text = ''
                else:
                    para.text = corrected
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_txt(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build plain text file with corrected text."""
        text = corrected_data.get('text', '')
        return text.encode('utf-8')
    
    def _create_correction_map(self, original: str, corrected: str) -> Dict[str, str]:
        """
        Create a mapping from original text segments to corrected versions.
        Uses simple line/paragraph matching.
        """
        corrections = {}
        
        # Split by common delimiters
        orig_parts = [p.strip() for p in original.split('\n') if p.strip()]
        corr_parts = [p.strip() for p in corrected.split('\n') if p.strip()]
        
        # Match by position
        for i, orig in enumerate(orig_parts):
            if i < len(corr_parts):
                corrections[orig] = corr_parts[i]
            else:
                corrections[orig] = orig  # Fallback to original
        
        return corrections

