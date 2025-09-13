# SigSecure AI

A hackathon prototype for **context-aware signature privacy** in sensitive documents, such as contracts, medical forms, and ID applications. SigSecure AI intelligently detects and protects signatures and related personal information (e.g., names, dates, addresses) while preserving document structure and legal value.

## Overview

SigSecure AI uses AI-powered models to:
- Detect signatures using a pretrained YOLOv8 model (fine-tuned for signatures).
- Identify related entities (names, dates, addresses) using Named Entity Recognition (NER) with spaCy.
- Establish contextual links between signatures and nearby text using Sentence-BERT.
- Apply dynamic redaction (black box, blur, or watermark) or highlighting based on user-selected privacy modes (signer, witness, medical).
- Provide a real-time preview of original and protected documents with a React-based frontend.
- Generate audit logs for compliance tracking.

## Features

- **Signature Detection**: Identifies signatures and classifies them as "signer" or "witness" based on nearby text context.
- **Context-Aware Redaction**: Protects sensitive information linked to signatures, adapting to document types (e.g., medical forms protect patient data but preserve doctor info).
- **Privacy Modes**: Options include "No Privacy," "Signer Privacy," "Witness Privacy," and "Medical Mode."
- **Redaction Styles**: Choose from black box, blur, or watermark redaction.
- **Highlight-Only Mode**: Highlights sensitive areas with red outlines for preview without permanent redaction.
- **Real-Time Preview**: Side-by-side display of original and protected documents with zoom functionality.
- **Audit Logs**: Tracks processing details (signatures detected, entities redacted, errors) in a JSON log.
- **AI Watermark**: Adds a "Privacy Protected by SigSecure AI" watermark to all processed documents.

## Directory Structure

```
SigSecure-AI/
├── backend/                    # Flask backend
│   ├── app/
│   │   ├── main.py            # Main API endpoints
│   ├── models/
│   │   ├── signature_detect.py # Signature detection logic
│   │   ├── text_pipeline.py   # Text detection and redaction
│   ├── venv/                  # Virtual environment
│   ├── .env                   # Environment variables
│   ├── requirements.txt       # Backend dependencies
├── data/                      # Input/output files
│   ├── redacted/              # Redacted PDFs (gitignored)
│   ├── audit_log.json         # Processing logs (gitignored)
│   ├── sample_photo.png       # Sample photo for testing
│   ├── signature.png          # Sample signature for testing
│   ├── noisy_signature.png    # Noisy signature for testing
├── frontend/                  # React frontend
│   ├── node_modules/          # Node dependencies
│   ├── public/
│   │   ├── index.html         # Main HTML file
│   │   ├── favicon.ico
│   │   ├── manifest.json
│   │   ├── robots.txt
│   ├── src/
│   │   ├── components/
│   │   │   ├── DocumentPreview.js  # Document preview component
│   │   │   ├── AuditLogs.js        # Audit log display
│   │   │   ├── ErrorMessage.js     # Error display
│   │   │   ├── UploadForm.js       # File upload form
│   │   ├── App.css                # Main styles
│   │   ├── App.js                 # Main React component
│   │   ├── index.css              # Global styles
│   │   ├── index.js               # React entry point
│   ├── .env
│   ├── package-lock.json
│   ├── package.json
├── scripts/                   # Test PDF generation scripts
│   ├── generate_test_pdf.py      # Generates standard test PDF
│   ├── generate_noisy_test_pdf.py # Generates noisy test PDF
│   ├── generate_medical_test_pdf.py # Generates medical test PDF
├── .gitattributes
├── .gitignore
├── README.md
```

## Setup Instructions

### Prerequisites
- **Python 3.8+**: For the backend.
- **Node.js 14+**: For the frontend.
- **Tesseract OCR**: System dependency for OCR functionality. Install it following the instructions [here](https://github.com/tesseract-ocr/tesseract#installing-tesseract).
- **Git**: For cloning the repository.

### Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd SigSecure-AI
   ```

2. **Backend Setup**:
   ```bash
   # Create and activate a virtual environment
   python -m venv backend/venv
   source backend/venv/bin/activate  # Linux/Mac
   backend\venv\Scripts\activate     # Windows

   # Install dependencies
   pip install -r backend/requirements.txt

   # Install spaCy model
   python -m spacy download en_core_web_sm
   ```

3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   ```

4. **Generate Test PDFs**:
   Run the scripts to generate sample PDFs for testing:
   ```bash
   cd scripts
   python generate_test_pdf.py
   python generate_noisy_test_pdf.py
   python generate_medical_test_pdf.py
   ```
   This creates `test.pdf`, `noisy_test.pdf`, and `medical_test.pdf` in the `data/` directory.

### Running the Application

1. **Start the Backend**:
   ```bash
   cd backend
   python app/main.py
   ```
   The Flask server will run on `http://localhost:5000`.

2. **Start the Frontend**:
   In a new terminal:
   ```bash
   cd frontend
   npm start
   ```
   The React app will open in your browser at `http://localhost:3000`.

3. **Using the Application**:
   - Open `http://localhost:3000` in your browser.
   - Upload a PDF (e.g., `data/test.pdf`, `data/noisy_test.pdf`, or `data/medical_test.pdf`) or any other PDF of your choice.
   - Select a **Privacy Mode** (No Privacy, Signer Privacy, Witness Privacy, Medical Mode).
   - Choose a **Redaction Style** (Black Box, Blur, Watermark).
   - Check **Highlight Only** to preview sensitive areas with red outlines instead of redacting.
   - Click **Upload & Process** to process the document.
   - View the side-by-side preview (original vs. protected) and download the processed file.
   - Check the **Audit Logs** section for a compliance summary.

**Note**: While you can upload any PDF, accuracy may vary depending on document quality (e.g., low-resolution scans, handwritten text, or unusual layouts).

## How It Works

1. **Signature Detection**: The backend uses a YOLOv8-based model (placeholder in `signature_detect.py`) to identify signatures in the PDF.
2. **Text Processing**: The `text_pipeline.py` script:
   - Performs OCR with Tesseract to extract text near signatures.
   - Uses Sentence-BERT to link signatures to relevant text (e.g., names, dates).
   - Applies NER (spaCy) to identify sensitive entities (PERSON, DATE, GPE).
   - Redacts or highlights based on the selected privacy mode and style.
3. **Frontend**: The React app provides a user-friendly interface for uploading files, selecting options, and viewing results.
4. **Audit Logs**: A JSON log (`data/audit_log.json`) records processing details, including signatures detected, entities redacted, and any errors.

## Constraints and Known Issues

- **Model Accuracy**: May vary with low-quality scans or handwritten text.
- **Complex Layouts**: Cluttered documents may lead to false positives or missed redactions.
- **Cross-Page Linking**: Signature-to-name matching across pages is under development.
- **Performance**: Real-time preview may be slower for large multi-page PDFs.

## Future Enhancements

- **Blockchain Anchoring**: To verify redaction authenticity.
- **Multilingual Support**: For documents in Indian and global languages.
- **AI Watermarking**: To trace privacy changes.
- **Voice Accessibility**: Guidance for visually impaired users.
- **Integration**: With platforms like DocuSign or Aadhaar eSign.

## Contributing

1. Fork the repository.
2. Create a branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

To add collaborators on GitHub:
1. Go to the repository on GitHub.
2. Navigate to **Settings > Collaborators**.
3. Enter your teammate’s GitHub username and send an invitation.
