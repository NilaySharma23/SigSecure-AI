from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pathlib import Path

def generate_test_pdf(output_path, signature_path=None, photo_path=None):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    # Page 1: Text + Signer Signature + Photo (for medical mode)
    c.drawString(100, height - 100, "Medical Test Document - Page 1")
    c.drawString(100, height - 200, "Patient: John Doe")
    if photo_path and Path(photo_path).exists():
        c.drawImage(photo_path, 300, height - 250, width=100, height=100)  # Square photo next to signature
    if signature_path and Path(signature_path).exists():
        c.drawImage(signature_path, 100, height - 250, width=150, height=50)
    else:
        c.drawString(100, height - 250, "Signature: ~~~~~")
    c.drawString(100, height - 300, "Doctor: Dr. Jane Smith")  # To test non-redaction of doctor info
    c.showPage()
    # Page 2: Text + Witness Signature
    c.drawString(100, height - 100, "Test Document - Page 2")
    c.drawString(100, height - 200, "Witness: Jane Smith")
    if signature_path and Path(signature_path).exists():
        c.drawImage(signature_path, 100, height - 250, width=150, height=50)
    else:
        c.drawString(100, height - 250, "Signature: ~~~~~")
    c.showPage()
    # Page 3: Text
    c.drawString(100, height - 100, "Test Document - Page 3")
    c.showPage()
    # Page 4: Text + Signer Signature
    c.drawString(100, height - 100, "Test Document - Page 4")
    c.drawString(100, height - 200, "Signer: John Doe")
    if signature_path and Path(signature_path).exists():
        c.drawImage(signature_path, 100, height - 250, width=150, height=50)
    else:
        c.drawString(100, height - 250, "Signature: ~~~~~")
    c.save()

if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / 'medical_test.pdf'  # New name for photo PDF
    signature_path = output_dir / 'signature.png'
    photo_path = output_dir / 'sample_photo.png'  # Add this
    generate_test_pdf(str(output_path), str(signature_path) if signature_path.exists() else None, str(photo_path) if photo_path.exists() else None)
    print(f"Generated medical test PDF at: {output_path}")