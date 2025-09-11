# scripts/generate_noisy_test_pdf.py
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz

def add_noise_to_image(image_path, output_path):
    img = cv2.imread(image_path)
    noise = np.random.normal(0, 25, img.shape).astype(np.uint8)
    noisy_img = cv2.add(img, noise)
    cv2.imwrite(str(output_path), noisy_img)

def generate_noisy_test_pdf(output_path, signature_path=None):
    output_path = Path(output_path)  # Ensure output_path is a Path object
    c = canvas.Canvas(str(output_path), pagesize=letter)  # Convert to string for canvas
    width, height = letter
    c.drawString(100, height - 100, "Test Document - Page 1")
    c.drawString(100, height - 200, "Signer: John Doe")
    if signature_path and Path(signature_path).exists():
        # Add noise to signature
        noisy_signature = output_path.parent / 'noisy_signature.png'
        add_noise_to_image(signature_path, noisy_signature)
        c.drawImage(str(noisy_signature), 100, height - 250, width=150, height=50)
    else:
        c.drawString(100, height - 250, "Signature: ~~~~~")
    c.save()

if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / 'noisy_test.pdf'
    signature_path = output_dir / 'signature.png'
    generate_noisy_test_pdf(output_path, signature_path if signature_path.exists() else None)
    print(f"Generated noisy test PDF at: {output_path}")