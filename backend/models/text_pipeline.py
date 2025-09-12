import fitz  # PyMuPDF for PDF handling
import pytesseract  # OCR
from PIL import Image  # For image handling in OCR
import spacy  # NER
import cv2  # For blur and preprocessing
import numpy as np  # For array handling
from pathlib import Path
from io import BytesIO
from pytesseract import Output  # For detailed OCR data
from sentence_transformers import SentenceTransformer, util  # For semantic linking
import torch  # Required for sentence-transformers
from datetime import datetime  # For timestamp in error logging
import json  # For audit log
from fuzzywuzzy import fuzz  # Added for fuzzy matching

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load Sentence-BERT model (run once)
bert_model = SentenceTransformer('all-MiniLM-L6-v2')

def detect_and_redact_text_near_signatures(input_file, sig_boxes, output_file, privacy_mode='none', redaction_style='black', highlight_only=False):
    """
    Detects and redacts text near signatures using OCR, NER, and Sentence-BERT.
    - Extracts text near sig_boxes.
    - Uses Sentence-BERT to filter signature-related text.
    - Uses NER to identify names, dates, addresses, phones in filtered text.
    - Redacts with black box, blur, or watermark based on redaction_style, or highlights with red outline if highlight_only=True.
    - Handles photos in medical mode.
    - Adds AI watermark to all outputs.
    - Saves redacted or highlighted PDF to output_file.
    Returns: redacted_path (str), entities_detected (dict: e.g., {"PERSON": 1, "DATE": 0, "GPE": 0})
    """
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)
        doc = fitz.open(input_path)
        entities_detected = {"PERSON": 0, "DATE": 0, "GPE": 0}  # Track by type
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
            # Preprocess image for better OCR: Convert to numpy array and enhance contrast
            img_array = np.array(img)
            img_array = cv2.convertScaleAbs(img_array, alpha=1.5, beta=50)  # Increase contrast
            img = Image.fromarray(img_array)
            # Perform OCR with detailed data
            ocr_data = pytesseract.image_to_data(img, output_type=Output.DICT)
            # Calculate average confidence (ignore -1 or 0 conf values which are non-text)
            conf_scores = [c for c in ocr_data['conf'] if c > 0]
            avg_conf = sum(conf_scores) / len(conf_scores) if conf_scores else 0
            # If average confidence is low (<50), retry with denoising
            if avg_conf < 50:
                # Apply light Gaussian blur to denoise
                img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
                img = Image.fromarray(img_array)
                ocr_data = pytesseract.image_to_data(img, output_type=Output.DICT)
            # Reconstruct full text and split into sentences using spaCy
            full_text = ' '.join([word for word in ocr_data['text'] if word.strip()])
            doc_text = nlp(full_text)
            sentences = [sent.text.strip() for sent in doc_text.sents if sent.text.strip()]
            linked_text = []
            if sentences:
                signature_context = "signer name"  # Context for BERT
                embeddings = bert_model.encode(sentences + [signature_context], convert_to_tensor=True)
                similarities = util.cos_sim(embeddings[:-1], embeddings[-1])
                linked_indices = [i for i, sim in enumerate(similarities[0]) if sim > 0.2]
                linked_text = [sentences[i] for i in linked_indices]
            # Fallback: use all text if no linked text found
            if not linked_text:
                linked_text = sentences if sentences else [full_text]
            # Run NER on filtered text
            text = ' '.join(linked_text)
            ner_doc = nlp(text)
            # Redact (or highlight) signature based on privacy_mode and style
            should_redact_sig = False
            if privacy_mode == 'signer' and sig['type'] == 'signer':
                should_redact_sig = True
            elif privacy_mode == 'witness' and sig['type'] == 'witness':
                should_redact_sig = True
            elif privacy_mode == 'medical':
                should_redact_sig = True  # Redact by default (patient/witness)
                if "doctor" in text.lower() or "md" in text.lower():
                    should_redact_sig = False  # Skip if doctor's info
            if should_redact_sig:
                sig_rect = fitz.Rect(bbox)  # Use the signature bbox
                if highlight_only:
                    # Highlight with red outline instead of redacting
                    page.draw_rect(sig_rect, color=(1, 0, 0), width=2)  # Red stroke, no fill
                else:
                    if redaction_style == 'black':
                        page.add_redact_annot(sig_rect, fill=(0, 0, 0))
                    elif redaction_style == 'blur':
                        try:
                            # Get pixmap for the exact bbox region
                            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=sig_rect)
                            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                            if pix.n == 4:
                                img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
                            else:
                                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                            # Apply blur
                            blurred = cv2.GaussianBlur(img_array, (15, 15), 5)
                            pixmap = fitz.Pixmap(fitz.csRGB, fitz.Rect(0, 0, pix.width, pix.height))
                            pixmap.set_rect(pixmap.irect, blurred.tobytes())
                            page.insert_image(sig_rect, pixmap=pixmap)
                        except Exception as e:
                            page.add_redact_annot(sig_rect, fill=(0, 0, 0))  # Fallback to black
                            continue  # Skip to next signature
                    elif redaction_style == 'watermark':
                        try:
                            page.insert_text((sig_rect.x0, sig_rect.y0), "REDACTED", fontsize=12, color=(1, 1, 1), fill=(0, 0, 0))
                        except Exception as e:
                            page.add_redact_annot(sig_rect, fill=(0, 0, 0))  # Fallback to black
                            continue  # Skip to next signature
            # Redact (or highlight) photo placeholder in medical mode
            if privacy_mode == 'medical' and sig.get('is_photo', False):
                if highlight_only:
                    page.draw_rect(sig_rect, color=(1, 0, 0), width=2)  # Highlight photo
                else:
                    page.add_redact_annot(sig_rect, text="ID PHOTO REDACTED", fill=(0, 0, 0), text_color=(1, 1, 1))
            # Process entities for redaction (or highlighting)
            for ent in ner_doc.ents:
                if ent.label_ in ["PERSON", "DATE", "GPE"]:  # "PHONE" not standard; use "MISC" or custom if needed
                    # Skip header-like entities
                    if "page" in ent.text.lower() or "document" in ent.text.lower():
                        continue
                    # Mode-dependent redaction for entities
                    should_redact_ent = False
                    if privacy_mode == 'none':
                        should_redact_ent = False
                    elif privacy_mode == 'signer' and sig['type'] == 'signer':
                        should_redact_ent = True
                    elif privacy_mode == 'witness' and sig['type'] == 'witness':
                        should_redact_ent = True
                    elif privacy_mode == 'medical':
                        should_redact_ent = True
                        if "doctor" in text.lower():
                            should_redact_ent = False
                    if should_redact_ent:
                        # Find approximate bbox for entity
                        ent_words = ent.text.split()
                        ent_left, ent_top, ent_right, ent_bottom = float('inf'), float('inf'), 0, 0
                        current_word_idx = 0
                        for i in range(len(ocr_data['text'])):
                            word = ocr_data['text'][i].strip()
                            if word and current_word_idx < len(ent_words):
                                # Fuzzy match with threshold (80% similarity)
                                if fuzz.ratio(word.lower(), ent_words[current_word_idx].lower()) > 80:
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
                            # Translate to page coordinates
                            page_left = clip_rect.x0 + (ent_left / 2)
                            page_top = clip_rect.y0 + (ent_top / 2)
                            page_right = clip_rect.x0 + (ent_right / 2)
                            page_bottom = clip_rect.y0 + (ent_bottom / 2)
                            ent_rect = fitz.Rect(page_left, page_top, page_right, page_bottom)
                            if highlight_only:
                                # Highlight with red outline
                                page.draw_rect(ent_rect, color=(1, 0, 0), width=2)  # Red stroke, no fill
                            else:
                                if redaction_style == 'black':
                                    page.add_redact_annot(ent_rect, fill=(0, 0, 0))
                                elif redaction_style == 'blur':
                                    try:
                                        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=ent_rect)
                                        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                                        if pix.n == 4:
                                            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
                                        else:
                                            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                                        blurred = cv2.GaussianBlur(img_array, (15, 15), 5)
                                        pixmap = fitz.Pixmap(fitz.csRGB, fitz.Rect(0, 0, pix.width, pix.height))
                                        pixmap.set_rect(pixmap.irect, blurred.tobytes())
                                        page.insert_image(ent_rect, pixmap=pixmap)
                                    except Exception as e:
                                        page.add_redact_annot(ent_rect, fill=(0, 0, 0))  # Fallback to black
                                        continue
                                elif redaction_style == 'watermark':
                                    try:
                                        page.insert_text((ent_rect.x0, ent_rect.y0), "REDACTED", fontsize=12, color=(1, 1, 1), fill=(0, 0, 0))
                                    except Exception as e:
                                        page.add_redact_annot(ent_rect, fill=(0, 0, 0))  # Fallback to black
                                        continue
                            # Increment count for this entity type (only if redacted or highlighted)
                            entities_detected[ent.label_] += 1
            # Apply all redactions on this page ONLY if not highlight_only
            if not highlight_only:
                page.apply_redactions()
        # Add AI watermark to all pages
        watermark_text = "Privacy Protected by SigSecure AI"
        for page in doc:
            page.insert_textbox(
                fitz.Rect(page.rect.width - 200, page.rect.height - 20, page.rect.width, page.rect.height),  # Bottom-right
                watermark_text,
                fontsize=8,
                color=(0.5, 0.5, 0.5),  # Gray
                overlay=True  # Place on top of content
            )
        # Save the document (highlighted or redacted)
        doc.save(output_path)
        doc.close()
        return str(output_path), entities_detected
    except Exception as e:
        # Log error to audit_log.json
        audit_log_path = Path(input_file).parent / 'audit_log.json'
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": Path(input_file).name,
            "error": f"Text pipeline failed: {str(e)}"
        }
        with open(audit_log_path, 'a') as f:
            json.dump(error_entry, f)
            f.write('\n')
        return None, {"PERSON": 0, "DATE": 0, "GPE": 0}  # Return empty dict on error