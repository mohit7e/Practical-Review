"""
Document Processor - Handles extraction and rebuilding of various document formats.
"""

import io
from typing import Dict, Any

import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

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
        """Extract text from PDF."""
        pages = []
        full_text = []
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({'page_num': i + 1, 'text': text})
                full_text.append(text)
        
        return {
            'type': 'pdf',
            'text': '\n\n'.join(full_text),
            'pages': pages,
            'page_count': len(pages)
        }
    
    def _extract_xlsx(self, content: bytes) -> Dict[str, Any]:
        """Extract text from Excel."""
        wb = load_workbook(io.BytesIO(content))
        sheets = []
        full_text = []
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            cells = []
            
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        cell_value = str(cell.value)
                        cells.append({
                            'row': cell.row,
                            'col': cell.column,
                            'value': cell_value
                        })
                        full_text.append(cell_value)
            
            sheets.append({'name': sheet_name, 'cells': cells})
        
        wb.close()
        return {'type': 'xlsx', 'text': ' '.join(full_text), 'sheets': sheets}
    
    def _extract_docx(self, content: bytes) -> Dict[str, Any]:
        """Extract text from Word document."""
        doc = Document(io.BytesIO(content))
        paragraphs = []
        full_text = []
        
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                paragraphs.append({'index': i, 'text': para.text})
                full_text.append(para.text)
        
        return {
            'type': 'docx',
            'text': '\n'.join(full_text),
            'paragraphs': paragraphs
        }
    
    def _extract_txt(self, content: bytes) -> Dict[str, Any]:
        """Extract text from plain text file."""
        text = content.decode('utf-8', errors='replace')
        return {'type': 'txt', 'text': text}
    
    # ===================== BUILDERS =====================
    
    def _build_pdf(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """
        Build PDF with the exact corrected text.
        Uses simple formatting - no special fonts or superscripts.
        Title is bolded, paragraphs have spacing between them.
        """
        corrected_text = corrected_data.get('text', '')
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        margin_left = 72
        margin_right = 72
        margin_top = 72
        margin_bottom = 72
        
        usable_width = width - margin_left - margin_right
        line_height = 16
        font_size = 11
        title_font_size = 14
        paragraph_spacing = 12  # Extra space between paragraphs
        
        y = height - margin_top
        
        # Split into paragraphs
        paragraphs = corrected_text.split('\n')
        is_first_paragraph = True
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                # Empty line - add paragraph spacing
                y -= paragraph_spacing
                if y < margin_bottom:
                    c.showPage()
                    y = height - margin_top
                continue
            
            # Check if this is a title (first non-empty paragraph or short line that looks like a header)
            is_title = is_first_paragraph or (len(paragraph) < 80 and paragraph.strip().istitle())
            
            if is_title and is_first_paragraph:
                # Bold title
                c.setFont("Helvetica-Bold", title_font_size)
                current_font = "Helvetica-Bold"
                current_size = title_font_size
                is_first_paragraph = False
            else:
                # Regular text
                c.setFont("Helvetica", font_size)
                current_font = "Helvetica"
                current_size = font_size
            
            # Word wrap the paragraph
            words = paragraph.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                text_width = c.stringWidth(test_line, current_font, current_size)
                
                if text_width <= usable_width:
                    current_line = test_line
                else:
                    # Draw current line
                    if current_line:
                        c.drawString(margin_left, y, current_line)
                        y -= line_height
                        
                        if y < margin_bottom:
                            c.showPage()
                            c.setFont(current_font, current_size)
                            y = height - margin_top
                    
                    current_line = word
            
            # Draw remaining text
            if current_line:
                c.drawString(margin_left, y, current_line)
                y -= line_height
            
            # Add spacing after each paragraph
            y -= paragraph_spacing
            
            if y < margin_bottom:
                c.showPage()
                y = height - margin_top
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_xlsx(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build Excel with corrected text."""
        wb = load_workbook(io.BytesIO(original))
        
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        sheets = original_data.get('sheets', [])
        original_text = corrected_data.get('original_text', '')
        
        # Create word mapping
        corrections = self._create_word_mapping(original_text, corrected_text)
        
        for sheet_info in sheets:
            sheet_name = sheet_info.get('name')
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for cell_info in sheet_info.get('cells', []):
                    row, col = cell_info['row'], cell_info['col']
                    original_value = cell_info['value']
                    corrected_value = self._apply_corrections(original_value, corrections)
                    ws.cell(row=row, column=col, value=corrected_value)
        
        buffer = io.BytesIO()
        wb.save(buffer)
        wb.close()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_docx(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build Word document with corrected text."""
        doc = Document(io.BytesIO(original))
        
        corrected_text = corrected_data.get('text', '')
        original_data = corrected_data.get('original_structure', {})
        paragraphs = original_data.get('paragraphs', [])
        
        # Create paragraph mapping
        corr_paras = [p for p in corrected_text.split('\n') if p.strip()]
        
        for i, para_info in enumerate(paragraphs):
            idx = para_info.get('index', 0)
            if idx < len(doc.paragraphs) and i < len(corr_paras):
                para = doc.paragraphs[idx]
                if para.runs:
                    para.runs[0].text = corr_paras[i]
                    for run in para.runs[1:]:
                        run.text = ''
                else:
                    para.text = corr_paras[i]
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_txt(self, corrected_data: Dict[str, Any], original: bytes) -> bytes:
        """Build plain text file."""
        return corrected_data.get('text', '').encode('utf-8')
    
    def _create_word_mapping(self, original: str, corrected: str) -> Dict[str, str]:
        """Create word-level mapping."""
        mapping = {}
        orig_words = original.split()
        corr_words = corrected.split()
        
        for i, orig in enumerate(orig_words):
            if i < len(corr_words) and orig != corr_words[i]:
                mapping[orig] = corr_words[i]
        
        return mapping
    
    def _apply_corrections(self, text: str, corrections: Dict[str, str]) -> str:
        """Apply corrections to text."""
        result = text
        for orig, corr in corrections.items():
            result = result.replace(orig, corr)
        return result
