"""
Document Processor - Handles extraction and rebuilding of various document formats.
Supports: PDF, XLSX, DOCX, TXT
"""

import io
import copy
from typing import Dict, Any

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from openpyxl import load_workbook

from docx import Document


class DocumentProcessor:
    """Handles document text extraction and rebuilding."""
    
    def extract_text(self, content: bytes, file_ext: str) -> Dict[str, Any]:
        """Extract text from document based on file type."""
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
        """Rebuild document with corrected text in original format."""
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
                for cell in row:
                    if cell.value is not None:
                        cell_value = str(cell.value)
                        cells.append({
                            'row': cell.row,
                            'col': cell.column,
                            'value': cell_value
                        })
                        sheet_text.append(cell_value)
            
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
        
        # Extract from tables
        tables = []
        for t_idx, table in enumerate(doc.tables):
            table_data = []
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    if cell.text.strip():
                        table_data.append({
                            'row': r_idx,
                            'col': c_idx,
                            'text': cell.text
                        })
                        full_text.append(cell.text)
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
        """
        Build PDF - returns corrected text as a simple PDF.
        Preserves page structure where possible.
        """
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        original_pages = original_data.get('pages', [])
        
        # Create correction mapping
        original_text = corrected_data.get('original_text', '')
        corrections = self._create_text_mapping(original_text, corrected_text)
        
        buffer = io.BytesIO()
        
        # Create a simple PDF with the corrected text
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Split text into pages based on original page breaks
        if original_pages:
            page_texts = corrected_text.split('\n\n')
            y_position = height - 72
            line_height = 14
            margin = 72
            max_width = width - (2 * margin)
            
            for page_text in page_texts:
                lines = page_text.split('\n')
                for line in lines:
                    if y_position < 72:
                        c.showPage()
                        y_position = height - 72
                    
                    # Wrap long lines
                    if line:
                        c.setFont("Helvetica", 11)
                        c.drawString(margin, y_position, line[:100])
                    y_position -= line_height
                
                y_position -= line_height  # Extra space between pages
        else:
            # Single page fallback
            y_position = height - 72
            for line in corrected_text.split('\n'):
                if y_position < 72:
                    c.showPage()
                    y_position = height - 72
                if line.strip():
                    c.setFont("Helvetica", 11)
                    c.drawString(72, y_position, line[:100])
                y_position -= 14
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_xlsx(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build Excel file with corrected text in cells."""
        original_wb = load_workbook(io.BytesIO(original))
        
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        sheets = original_data.get('sheets', [])
        original_text = corrected_data.get('original_text', '')
        
        # Create word-level mapping
        corrections = self._create_word_mapping(original_text, corrected_text)
        
        # Apply corrections to cells
        for sheet_info in sheets:
            sheet_name = sheet_info.get('name')
            if sheet_name in original_wb.sheetnames:
                ws = original_wb[sheet_name]
                for cell_info in sheet_info.get('cells', []):
                    row, col = cell_info['row'], cell_info['col']
                    original_value = cell_info['value']
                    
                    # Apply word-level corrections
                    corrected_value = self._apply_corrections(original_value, corrections)
                    ws.cell(row=row, column=col, value=corrected_value)
        
        buffer = io.BytesIO()
        original_wb.save(buffer)
        original_wb.close()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_docx(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build Word document with corrected text, preserving formatting."""
        doc = Document(io.BytesIO(original))
        
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        paragraphs = original_data.get('paragraphs', [])
        original_text = corrected_data.get('original_text', '')
        
        # Create paragraph-level mapping
        orig_paras = [p.strip() for p in original_text.split('\n') if p.strip()]
        corr_paras = [p.strip() for p in corrected_text.split('\n') if p.strip()]
        
        para_map = {}
        for i, op in enumerate(orig_paras):
            if i < len(corr_paras):
                para_map[op] = corr_paras[i]
        
        # Apply corrections to paragraphs
        for para_info in paragraphs:
            idx = para_info.get('index', 0)
            if idx < len(doc.paragraphs):
                original_para_text = para_info.get('text', '')
                corrected_para = para_map.get(original_para_text, original_para_text)
                
                para = doc.paragraphs[idx]
                if para.runs:
                    # Preserve formatting by updating first run
                    para.runs[0].text = corrected_para
                    for run in para.runs[1:]:
                        run.text = ''
                else:
                    para.text = corrected_para
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_txt(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build plain text file with corrected text."""
        text = corrected_data.get('text', '')
        return text.encode('utf-8')
    
    def _create_text_mapping(self, original: str, corrected: str) -> Dict[str, str]:
        """Create a mapping from original text to corrected text."""
        mapping = {}
        
        orig_lines = original.split('\n')
        corr_lines = corrected.split('\n')
        
        for i, orig_line in enumerate(orig_lines):
            if i < len(corr_lines) and orig_line.strip():
                mapping[orig_line.strip()] = corr_lines[i].strip()
        
        return mapping
    
    def _create_word_mapping(self, original: str, corrected: str) -> Dict[str, str]:
        """Create word-level mapping for corrections."""
        mapping = {}
        
        orig_words = original.split()
        corr_words = corrected.split()
        
        for i, orig_word in enumerate(orig_words):
            if i < len(corr_words) and orig_word != corr_words[i]:
                mapping[orig_word] = corr_words[i]
        
        return mapping
    
    def _apply_corrections(self, text: str, corrections: Dict[str, str]) -> str:
        """Apply word-level corrections to text."""
        result = text
        for orig, corr in corrections.items():
            result = result.replace(orig, corr)
        return result
