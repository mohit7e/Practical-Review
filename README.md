# Refine — AI Document Correction

A beautiful, minimal application that corrects spelling, grammar, and factual accuracy in your documents. Upload PDF, XLSX, DOCX, or TXT files and receive the corrected version in the same format.

![Refine](https://img.shields.io/badge/Refine-Document%20Correction-e07a5f)

## Features

- **Multi-format Support**: PDF, XLSX, DOCX, TXT files
- **AI-Powered Corrections**: Spelling, grammar, and factual accuracy
- **Same Format Output**: Returns corrected document in original format
- **Beautiful UI**: Fluid, minimal, modern interface
- **Change Tracking**: See exactly what was corrected and why
- **Side-by-side Preview**: Compare original and corrected text

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API key (for AI corrections)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
# On Windows: set OPENAI_API_KEY=your-api-key-here

# Run the server
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install


# Run the development server
npm run dev
```

The UI will be available at `http://localhost:5173`

## Usage

1. Open the web interface at `http://localhost:5173`
2. Drag and drop a document or click to browse
3. Wait for AI processing
4. Review the corrections made
5. Download the corrected file

## API Endpoints

### `POST /upload`
Upload a document for correction and receive the corrected file.

**Request**: `multipart/form-data` with file

**Response**: Corrected file download

### `POST /preview`
Get a preview of corrections without downloading.

**Request**: `multipart/form-data` with file

**Response**:
```json
{
  "original": "Original text...",
  "corrected": "Corrected text...",
  "changes": [
    {
      "type": "spelling|grammar|factual",
      "original": "...",
      "corrected": "...",
      "explanation": "..."
    }
  ],
  "summary": "Summary of corrections"
}
```

### `GET /health`
Health check endpoint.

## Configuration

Set the following environment variable:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes (for AI features) |

Without an API key, the app falls back to basic spelling corrections.

## Supported Formats

| Format | Read | Write | Notes |
|--------|------|-------|-------|
| PDF | ✅ | ✅ | Extracts text, rebuilds with formatting |
| XLSX | ✅ | ✅ | Preserves cell structure and sheets |
| DOCX | ✅ | ✅ | Maintains paragraph formatting |
| TXT | ✅ | ✅ | Plain text processing |

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI application
│   ├── document_processor.py # File extraction & rebuilding
│   ├── ai_corrector.py      # OpenAI integration
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── index.css        # Styling
│   │   └── main.jsx         # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Technology Stack

**Backend**
- FastAPI - Modern Python web framework
- OpenAI GPT-4o - AI text correction
- pypdf/pdfplumber - PDF processing
- openpyxl - Excel processing
- python-docx - Word document processing
- ReportLab - PDF generation

**Frontend**
- React 18 - UI framework
- Vite - Build tool
- Framer Motion - Animations
- Custom CSS - Styling

## License

MIT

