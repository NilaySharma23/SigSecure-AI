import fitz  # PyMuPDF for PDF handling
import pytesseract  # OCR
from PIL import Image  # For image handling in OCR
import spacy  # NER
import cv2  # For blur and preprocessing
import numpy as np
from pathlib import Path
from io import BytesIO
from pytesseract import Output  # For detailed OCR data
from sentence_transformers import SentenceTransformer, util  # For semantic linking
import torch  # Required for sentence-transformers
import json
import datetime

# Load spaCy model
nlp = spacy.load("en_core_web_sm")
# Load Sentence-BERT model (run once)
bert_model = SentenceTransformer('all-MiniLM-L6-v2')

def preprocess_image_for_ocr(img):
    """Preprocess image for OCR: enhance contrast and denoise."""
    img_array = np.array(img)
    # Increase contrast
    img_array = cv2.convertScaleAbs(img_array, alpha=1.5, beta=50)
    # Denoise
    img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
    return Image.fromarray(img_array)

def detect_and_redact_text_near_signatures(input_file, sig_boxes, output_file, privacy_mode='none', redaction_style='black'):
    """
    Detects and redacts text near signatures using OCR, NER, and Sentence-BERT.
    - Extracts text near sig_boxes.
    - Uses Sentence-BERT to filter signature-related text.
    - Uses NER to identify names, dates, addresses, phones in filtered text.
    - Redacts with black box, blur, or watermark based on redaction_style.
    - Handles photos in medical mode.
    - Preprocesses images for better OCR and retries on low confidence.
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
            # Expand bbox for context (increased to capture more text)
            expand_px = 300
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

            # Preprocess image for OCR
            img = preprocess_image_for_ocr(img)

            # Perform OCR with detailed data
            ocr_data = pytesseract.image_to_data(img, output_type=Output.DICT)
            # Check OCR confidence
            confidences = [float(c) for c in ocr_data['conf'] if c != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Retry with different preprocessing if confidence is low
            if avg_confidence < 50:
                img_array = np.array(img)
                img_array = cv2.convertScaleAbs(img_array, alpha=2.0, beta=100)
                img_array = cv2.GaussianBlur(img_array, (5, 5), 0)
                img = Image.fromarray(img_array)
                ocr_data = pytesseract.image_to_data(img, output_type=Output.DICT)
                confidences = [float(c) for c in ocr_data['conf'] if c != '-1']
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                with open(input_path.parent / 'audit_log.json', 'a') as f:
                    json.dump({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "file": input_path.name,
                        "event": "OCR retry",
                        "avg_confidence_before": avg_confidence,
                        "details": "Retried OCR with stronger contrast and denoising"
                    }, f)
                    f.write('\n')

            # Log OCR output for debugging
            with open(input_path.parent / 'audit_log.json', 'a') as f:
                json.dump({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "file": input_path.name,
                    "event": "OCR output",
                    "text": ocr_data['text'],
                    "confidences": confidences
                }, f)
                f.write('\n')

            # Reconstruct full text and split into sentences using spaCy
            full_text = ' '.join([word for word in ocr_data['text'] if word.strip()])
            doc_text = nlp(full_text)
            sentences = [sent.text.strip() for sent in doc_text.sents if sent.text.strip()]
            linked_text = []

            if sentences:
                signature_context = "signer name"
                embeddings = bert_model.encode(sentences + [signature_context], convert_to_tensor=True)
                similarities = util.cos_sim(embeddings[:-1], embeddings[-1])
                linked_indices = [i for i, sim in enumerate(similarities[0]) if sim > 0.15]  # Lowered threshold
                linked_text = [sentences[i] for i in linked_indices]

            # Fallback: use all text if no linked text found
            if not linked_text:
                linked_text = sentences if sentences else [full_text]

            # Run NER on filtered text
            text = ' '.join(linked_text)
            ner_doc = nlp(text)

            # Log NER output for debugging
            with open(input_path.parent / 'audit_log.json', 'a') as f:
                json.dump({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "file": input_path.name,
                    "event": "NER output",
                    "entities": [(ent.text, ent.label_) for ent in ner_doc.ents]
                }, f)
                f.write('\n')

            # Redact signature based on privacy_mode and style
            should_redact_sig = False
            if privacy_mode == 'signer' and sig['type'] == 'signer':
                should_redact_sig = True
            elif privacy_mode == 'witness' and sig['type'] == 'witness':
                should_redact_sig = True
            elif privacy_mode == 'medical':
                should_redact_sig = True
                if "doctor" in text.lower() or "md" in text.lower():
                    should_redact_sig = False

            if should_redact_sig:
                if redaction_style == 'black':
                    page.add_redact_annot(fitz.Rect(bbox), fill=(0, 0, 0))
                elif redaction_style == 'blur':
                    try:
                        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=fitz.Rect(bbox))
                        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                        if pix.n == 4:
                            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
                        else:
                            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                        blurred = cv2.GaussianBlur(img_array, (15, 15), 5)
                        pixmap = fitz.Pixmap(fitz.csRGB, fitz.Rect(0, 0, pix.width, pix.height))
                        pixmap.set_rect(pixmap.irect, blurred.tobytes())
                        page.insert_image(fitz.Rect(bbox), pixmap=pixmap)
                    except Exception as e:
                        page.add_redact_annot(fitz.Rect(bbox), fill=(0, 0, 0))
                        continue
                elif redaction_style == 'watermark':
                    try:
                        page.insert_text((bbox[0], bbox[1]), "REDACTED", fontsize=12, color=(1, 1, 1), fill=(0, 0, 0))
                    except Exception as e:
                        page.add_redact_annot(fitz.Rect(bbox), fill=(0, 0, 0))
                        continue

            # Redact photo placeholder in medical mode
            if privacy_mode == 'medical' and sig.get('is_photo', False):
                page.add_redact_annot(fitz.Rect(bbox), text="ID PHOTO REDACTED", fill=(0, 0, 0), text_color=(255, 255, 255))

            # Process entities for redaction
            for ent in ner_doc.ents:
                if ent.label_ in ["PERSON", "DATE", "GPE"]:
                    if "page" in ent.text.lower() or "document" in ent.text.lower():
                        continue
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
                        ent_words = ent.text.split()
                        ent_left, ent_top, ent_right, ent_bottom = float('inf'), float('inf'), 0, 0
                        current_word_idx = 0
                        i = 0
                        while i < len(ocr_data['text']) and current_word_idx < len(ent_words):
                            word = ocr_data['text'][i].strip()
                            if word and word in text and word.lower() == ent_words[current_word_idx].lower():
                                left = ocr_data['left'][i]
                                top = ocr_data['top'][i]
                                width = ocr_data['width'][i]
                                height = ocr_data['height'][i]
                                ent_left = min(ent_left, left)
                                ent_top = min(ent_top, top)
                                ent_right = max(ent_right, left + width)
                                ent_bottom = max(ent_bottom, top + height)
                                current_word_idx += 1
                            i += 1
                        if ent_left != float('inf'):
                            page_left = clip_rect.x0 + (ent_left / 2)
                            page_top = clip_rect.y0 + (ent_top / 2)
                            page_right = clip_rect.x0 + (ent_right / 2)
                            page_bottom = clip_rect.y0 + (ent_bottom / 2)
                            ent_rect = fitz.Rect(page_left, page_top, page_right, page_bottom)
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
                                    page.add_redact_annot(ent_rect, fill=(0, 0, 0))
                                    continue
                            elif redaction_style == 'watermark':
                                try:
                                    page.insert_text((ent_rect.x0, ent_rect.y0), "REDACTED", fontsize=12, color=(1, 1, 1), fill=(0, 0, 0))
                                except Exception as e:
                                    page.add_redact_annot(ent_rect, fill=(0, 0, 0))
                                    continue
                            entities_detected += 1

            # Apply all redactions on this page
            page.apply_redactions()

        # Save the redacted document
        doc.save(output_path)
        doc.close()
        return str(output_path), entities_detected

    except Exception as e:
        # Log detailed error to audit_log.json
        with open(input_path.parent / 'audit_log.json', 'a') as f:
            json.dump({
                "timestamp": datetime.datetime.now().isoformat(),
                "file": input_path.name,
                "error": f"Text pipeline failed: {str(e)}",
                "details": f"Failed during processing of {input_path}"
            }, f)
            f.write('\n')
        return None, 0