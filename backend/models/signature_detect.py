# backend/models/signature_detect.py
import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
import spacy  # For text context
from scipy.spatial.distance import cdist  # For merging contours

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def detect_signatures(file_path):
    try:
        file_path = Path(file_path)
        signatures = []
        doc = fitz.open(file_path)
        DPI = 200
        SCALE = DPI / 72.0
        
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
            
            # Dilate to connect disconnected signature strokes
            kernel = np.ones((5, 5), np.uint8)
            thresh = cv2.dilate(thresh, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Merge close contours
            if contours:
                boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 1000]  # Increased to reduce over-detection
                if boxes:
                    centers = [(x + w/2, y + h/2) for x,y,w,h in boxes]
                    dists = cdist(centers, centers)
                    merged = []
                    visited = [False] * len(boxes)
                    for i in range(len(boxes)):
                        if not visited[i]:
                            group = [i]
                            for j in range(i+1, len(boxes)):
                                if dists[i][j] < 100:  # Merge if centers <100px apart
                                    group.append(j)
                                    visited[j] = True
                            # Merge group into one bbox
                            gx = min(boxes[k][0] for k in group)
                            gy = min(boxes[k][1] for k in group)
                            gw = max(boxes[k][0] + boxes[k][2] for k in group) - gx
                            gh = max(boxes[k][1] + boxes[k][3] for k in group) - gy
                            merged.append((gx, gy, gw, gh))
                    for x, y, w, h in merged:
                        if w > 150 and h > 40:  # Increased min size for signatures; avoids thin lines
                            # Ignore top 10% of page (headers)
                            if y < pix.height * 0.1:
                                continue
                            # Extract nearby text for type classification (placeholder)
                            expand_rect = fitz.Rect(max(0, x/SCALE-100), max(0, y/SCALE-100), (x+w)/SCALE+100, (y+h)/SCALE+100)
                            nearby_text = page.get_text("text", clip=expand_rect).lower()
                            sig_type = "witness" if "witness" in nearby_text else "signer"
                            signatures.append({
                                "bbox": [x / SCALE, y / SCALE, (x + w) / SCALE, (y + h) / SCALE],
                                "type": sig_type,
                                "page": page_num + 1,
                                "is_photo": abs(w/h - 1) < 0.3 and w * h > 50000  # Flag as photo if near-square and large
                            })
        
        doc.close()
        return signatures  # Return list of dicts directly (adjusted to match main.py expectation)
    
    except Exception as e:
        return []  # Return empty list on error; log if needed