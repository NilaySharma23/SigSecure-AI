# backend/models/signature_detect.py

import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path

def detect_signatures(file_path):
    try:
        file_path = Path(file_path)
        signatures = []
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=200)  # Higher DPI for better detection accuracy
            # Convert pixmap to numpy array for OpenCV
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:  # Handle alpha channel if present
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Threshold to detect dark regions (signatures)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)  # Adjust threshold as needed
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size (adjust based on typical signature dimensions)
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > 50 and h > 20:  # Filter out small noise; tune these values
                    # For now, default to "signer" type (teammate can add classification logic later)
                    signatures.append({
                        "bbox": [x, y, x + w, y + h],
                        "type": "signer",  # Placeholder; can be enhanced to detect "witness" etc.
                        "page": page_num + 1
                    })
        
        doc.close()
        return signatures  # Return list of dicts directly (adjusted to match main.py expectation)
    
    except Exception as e:
        return []  # Return empty list on error; log if needed