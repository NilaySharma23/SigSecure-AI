# backend/app/main.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))  # Add backend/ to path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import json
import datetime
import traceback
from models.signature_detect import detect_signatures
from models.text_pipeline import detect_and_redact_text_near_signatures

app = Flask(__name__)
CORS(app)
load_dotenv()
# Set UPLOAD_FOLDER to the data/ directory in the project root
BASE_DIR = Path(__file__).resolve().parent.parent  # Go up two levels from app/ to SigSecure-AI/
UPLOAD_FOLDER = BASE_DIR / 'data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
OUTPUT_FOLDER = UPLOAD_FOLDER / 'redacted'
# Ensure directories exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
app.config['DEBUG'] = True

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Backend is running"})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file selected"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files are supported"}), 400
        privacy_mode = request.form.get('privacy_mode', 'none')
        redaction_style = request.form.get('redaction_style', 'black')  # Default to black, allow override
        filename = secure_filename(file.filename)
        input_path = UPLOAD_FOLDER / filename
        file.save(input_path)
        signatures = detect_signatures(str(input_path))
        redacted_filename = f'redacted_{filename}'
        redacted_path = OUTPUT_FOLDER / redacted_filename
        redacted_path_str, entity_count = detect_and_redact_text_near_signatures(
            str(input_path), signatures, str(redacted_path), privacy_mode, redaction_style
        )
        if redacted_path_str is None:
            raise Exception("Redaction failed")
        audit_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": filename,
            "privacy_mode": privacy_mode,
            "redaction_style": redaction_style,
            "signatures_detected": len(signatures),
            "entities_redacted": entity_count,
            "error": None
        }
        with open(UPLOAD_FOLDER / 'audit_log.json', 'a') as f:
            json.dump(audit_log, f)
            f.write('\n')
        return send_file(redacted_path_str, as_attachment=True, download_name=redacted_filename)
    except Exception as e:
        error_details = f"{str(e)}\n{traceback.format_exc()}"  # Capture full stack trace
        audit_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": filename if 'filename' in locals() else "unknown",
            "privacy_mode": privacy_mode if 'privacy_mode' in locals() else "unknown",
            "redaction_style": redaction_style if 'redaction_style' in locals() else "unknown",
            "signatures_detected": 0,
            "entities_redacted": 0,
            "error": error_details
        }
        with open(UPLOAD_FOLDER / 'audit_log.json', 'a') as f:
            json.dump(audit_log, f)
            f.write('\n')
        return jsonify({"error": str(e)}), 500

@app.route('/api/audit_log', methods=['GET'])
def get_audit_log():
    audit_log_path = UPLOAD_FOLDER / 'audit_log.json'
    try:
        with open(audit_log_path, 'r', encoding='utf-8') as f:
            logs = [json.loads(line) for line in f]
        return jsonify(logs)
    except FileNotFoundError:
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to read audit log: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)