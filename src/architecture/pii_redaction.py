import cv2
import re
import numpy as np

# Mocking pytesseract for environment where it might not be installed natively
try:
    import pytesseract
except ImportError:
    pytesseract = None

PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "CreditCard": r"\b(?:\d[ -]*?){13,16}\b",
    "Email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
}

def detect_and_blur_pii(image_path, output_path):
    """
    Offline PII Redaction Pipeline (Regex + OpenCV).
    Reads an image, uses OCR to find text bounding boxes,
    matches text against PII regex filters, and blurs sensitive regions.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image at {image_path}")
    
    if pytesseract is None:
        print("[Warning] pytesseract not installed. Returning original image.")
        cv2.imwrite(output_path, img)
        return
        
    # Get bounding box estimates
    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    n_boxes = len(d['text'])
    for i in range(n_boxes):
        if int(d['conf'][i]) > 60:  # Confidence threshold
            text = d['text'][i]
            
            # Check for PII
            is_pii = False
            for pii_type, pattern in PII_PATTERNS.items():
                if re.search(pattern, text):
                    is_pii = True
                    print(f"Detected {pii_type} at word: {text}")
                    break
            
            if is_pii:
                (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                
                # Extract region of interest
                roi = img[y:y+h, x:x+w]
                
                # Apply Gaussian Blur
                blurred_roi = cv2.GaussianBlur(roi, (51, 51), 0)
                
                # Put blurred ROI back into image
                img[y:y+h, x:x+w] = blurred_roi
                
    cv2.imwrite(output_path, img)
    print(f"Saved redacted image to {output_path}")

if __name__ == "__main__":
    print("PII Redaction Pipeline Loaded.")
