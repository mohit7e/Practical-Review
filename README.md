# Practical Review

AI-powered document correction for spelling, grammar, and factual accuracy.

## Features

- **Multi-format support**: PDF, XLSX, DOCX, TXT
- **AI corrections**: Spelling, grammar, and factual accuracy
- **Same format output**: Returns corrected document in original format
- **Change tracking**: See what was corrected and why

## Quick Start

### 1. Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AI

Create `backend/.env`:
```
AWS_BEARER_TOKEN_BEDROCK=your_token_here
AWS_REGION=us-east-1
```

### 3. Run

```bash
./start.sh
```

Or manually:
```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate && python main.py

# Terminal 2 - Frontend  
cd frontend && python3 -m http.server 3000
```

Open http://localhost:3000

## API

- `POST /upload` - Upload and get corrected file
- `POST /preview` - Preview corrections as JSON
- `GET /health` - Check status

## Project Structure

```
├── backend/
│   ├── main.py              # API server
│   ├── document_processor.py # File handling
│   ├── ai_corrector.py      # AI integration
│   └── requirements.txt
├── frontend/
│   └── index.html           # Web UI
├── start.sh                  # Startup script
└── README.md
```

## Requirements

- Python 3.9+
- AWS Bedrock access (for AI features)
