# SigSecure AI
Hackathon prototype for context-aware signature privacy in sensitive documents.

## Setup
### Backend
1. Create virtual env: `python -m venv backend/venv`
2. Activate: `source backend/venv/bin/activate` (Linux/Mac) or `backend\venv\Scripts\activate` (Windows)
3. Install deps: `pip install -r backend/requirements.txt`
4. Install spaCy model: `python -m spacy download en_core_web_sm`
5. Run: `cd backend && flask run`

### Frontend
1. Install deps: `cd frontend && npm install`
2. Run: `npm start`

### Dependencies
- Install Tesseract OCR (system dependency): https://github.com/tesseract-ocr/tesseract#installing-tesseract