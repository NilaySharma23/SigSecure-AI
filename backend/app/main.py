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
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Go up three levels from app/ to SigSecure-AI/
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
        redaction_style = request.form.get('redaction_style', 'black')  # Default to black
        highlight_only = request.form.get('highlight_only', 'false').lower() == 'true'  # Parse as boolean
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = secure_filename(file.filename)
        filename = f"{timestamp}_{original_filename}"
        input_path = UPLOAD_FOLDER / filename
        file.save(input_path)
        signatures = detect_signatures(str(input_path))
        redacted_filename = f'redacted_{filename}' if not highlight_only else f'highlighted_{filename}'
        redacted_path = OUTPUT_FOLDER / redacted_filename
        redacted_path_str, entities_detected = detect_and_redact_text_near_signatures(
            str(input_path), signatures, str(redacted_path), privacy_mode, redaction_style, highlight_only
        )
        # Clean up the temporary input file
        try:
            input_path.unlink()  # Delete the original uploaded file
        except Exception as cleanup_error:
            print(f"Failed to delete temporary file {input_path}: {cleanup_error}")
        if redacted_path_str is None:
            raise Exception("Redaction failed")
        audit_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": original_filename,
            "privacy_mode": privacy_mode,
            "redaction_style": redaction_style,
            "signatures_detected": len(signatures),
            "entities_redacted": entities_detected,  # Dict from text_pipeline
            "highlight_only": highlight_only,  # New field
            "error": None
        }
        with open(UPLOAD_FOLDER / 'audit_log.json', 'a') as f:
            json.dump(audit_log, f)
            f.write('\n')
        return send_file(redacted_path_str, as_attachment=True, download_name=redacted_filename)
    except Exception as e:
        error_details = f"{str(e)}\n{traceback.format_exc()}"  # Capture full stack trace
        filename = file.filename if 'file' in locals() else "unknown"
        privacy_mode = request.form.get('privacy_mode', 'unknown') if 'request' in locals() else "unknown"
        redaction_style = request.form.get('redaction_style', 'unknown') if 'request' in locals() else "unknown"
        highlight_only = request.form.get('highlight_only', 'false').lower() == 'true'  # Include in error log
        signatures_detected = len(signatures) if 'signatures' in locals() else 0
        audit_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": filename,
            "privacy_mode": privacy_mode,
            "redaction_style": redaction_style,
            "highlight_only": highlight_only,  # New field
            "signatures_detected": signatures_detected,
            "entities_redacted": {"PERSON": 0, "DATE": 0, "GPE": 0},  # Empty dict on error
            "error": error_details
        }
        with open(UPLOAD_FOLDER / 'audit_log.json', 'a') as f:
            json.dump(audit_log, f)
            f.write('\n')
        # Clean up the temporary input file on error (if it exists)
        if 'input_path' in locals():
            try:
                input_path.unlink()
            except Exception as cleanup_error:
                print(f"Failed to delete temporary file {input_path}: {cleanup_error}")
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
@app.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    audit_log_path = UPLOAD_FOLDER / 'audit_log.json'
    try:
        with open(audit_log_path, 'w') as f:
            pass
        return jsonify({"status": "Logs cleared"})
    except Exception as e:
        return jsonify({"error": f"Failed to clear logs: {str(e)}"}), 500
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Get port from environment
    app.run(host='0.0.0.0', port=port, debug=False)
