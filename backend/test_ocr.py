import pytesseract
from PIL import Image
from pytesseract import Output

# Set path if needed
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'  # Adjust

# Test on one debug image (replace with actual path)
img = Image.open('debug_page_1_enhanced.png')
data = pytesseract.image_to_data(img, output_type=Output.DICT, lang='eng')
print(data['text'])