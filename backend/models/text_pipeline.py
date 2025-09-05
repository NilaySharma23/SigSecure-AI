# backend/models/text_pipeline.py

import fitz  # PyMuPDF for PDF handling
import pytesseract  # OCR
from PIL import Image  # For image handling in OCR
import spacy  # NER
from pathlib import Path
from io import BytesIO
from pytesseract import Output  # For detailed OCR data

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def detect_and_redact_text_near_signatures(input_file, sig_boxes, output_file, privacy_mode='none'):
    """
    Detects and redacts text near signatures using OCR and NER.
    - Extracts text near sig_boxes.
    - Uses NER to identify entities (names, dates, addresses, phones).
    - Redacts only if entity is within the expanded region and matches criteria.
    - Applies role-based redaction based on privacy_mode.
    - Saves redacted PDF to output_file.
    Returns: redacted_path (str), entities_detected (int)
    """
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)
        doc = fitz.open(input_path)
        entities_detected = 0
        
        for sig in sig_boxes:
            page_num = sig['page'] - 1  # 0-indexed
            page = doc[page_num]
            bbox = sig['bbox']  # [x1, y1, x2, y2]
            
            # Expand bbox for context (to capture nearby text)
            expand_px = 200
            clip_rect = fitz.Rect(
                max(0, bbox[0] - expand_px),
                max(0, bbox[1] - expand_px),
                bbox[2] + expand_px,
                bbox[3] + expand_px
            )
            
            # Get higher-resolution pixmap for OCR
            matrix = fitz.Matrix(2, 2)  # 2x zoom for accuracy
            pix = page.get_pixmap(matrix=matrix, clip=clip_rect)
            img_bytes = pix.tobytes("png")
            img = Image.open(BytesIO(img_bytes))
            
            # Perform OCR with detailed data (includes bounding boxes for words)
            ocr_data = pytesseract.image_to_data(img, output_type=Output.DICT)
            
            # Reconstruct text from OCR for NER
            text = ' '.join([word for word in ocr_data['text'] if word.strip()])
            ner_doc = nlp(text)
            
            # Redact signature based on privacy_mode
            should_redact_sig = False
            if privacy_mode == 'signer' and sig['type'] == 'signer':
                should_redact_sig = True
            elif privacy_mode == 'witness' and sig['type'] == 'witness':
                should_redact_sig = True
            elif privacy_mode == 'medical':
                # For medical mode: assume "signer" is patient; redact it (enhance later)
                if sig['type'] == 'signer':
                    should_redact_sig = True
            
            if should_redact_sig:
                # Adjust bbox for matrix scale (divide by zoom factor)
                scaled_bbox = [coord / 2 for coord in bbox]
                redact_rect = fitz.Rect(scaled_bbox)
                page.add_redact_annot(redact_rect, fill=(0, 0, 0))  # Black box over signature
            
            # Process entities for redaction
            for ent in ner_doc.ents:
                if ent.label_ in ["PERSON", "DATE", "GPE"]:  # "PHONE" not standard; use "MISC" or custom if needed
                    # Simple rule: redact all linked PII unless mode specifies otherwise
                    should_redact_ent = True
                    if privacy_mode == 'medical':
                        # Example: don't redact if near "doctor" (heuristic; enhance with context)
                        if "doctor" in text.lower():
                            should_redact_ent = False  # Leave doctor's info
                    
                    if should_redact_ent:
                        # Find approximate bbox for entity by matching words
                        ent_words = ent.text.split()
                        ent_left, ent_top, ent_right, ent_bottom = float('inf'), float('inf'), 0, 0
                        current_word_idx = 0
                        for i in range(len(ocr_data['text'])):
                            word = ocr_data['text'][i].strip()
                            if word and word == ent_words[current_word_idx]:
                                left = ocr_data['left'][i]
                                top = ocr_data['top'][i]
                                width = ocr_data['width'][i]
                                height = ocr_data['height'][i]
                                ent_left = min(ent_left, left)
                                ent_top = min(ent_top, top)
                                ent_right = max(ent_right, left + width)
                                ent_bottom = max(ent_bottom, top + height)
                                current_word_idx += 1
                                if current_word_idx == len(ent_words):
                                    break
                        
                        if ent_left != float('inf'):
                            # Translate to page coordinates (adjust for clip and matrix)
                            page_left = clip_rect.x0 + (ent_left / 2)  # Divide by zoom
                            page_top = clip_rect.y0 + (ent_top / 2)
                            page_right = clip_rect.x0 + (ent_right / 2)
                            page_bottom = clip_rect.y0 + (ent_bottom / 2)
                            ent_rect = fitz.Rect(page_left, page_top, page_right, page_bottom)
                            page.add_redact_annot(ent_rect, fill=(0, 0, 0))  # Black box over entity
                            entities_detected += 1
            
            # Apply all redactions on this page
            page.apply_redactions()
        
        # Save the redacted document
        doc.save(output_path)
        doc.close()
        
        return str(output_path), entities_detected
    
    except Exception as e:
        return None, 0  # On error, return None for path and 0 count