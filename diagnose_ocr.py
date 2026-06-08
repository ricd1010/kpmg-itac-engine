import paddleocr
from paddleocr import PaddleOCR
import inspect
import numpy as np

print(f"PaddleOCR version: {paddleocr.__version__}")

ocr = PaddleOCR(use_angle_cls=True, lang='ch')

print("\n--- PaddleOCR.ocr signature ---")
print(inspect.signature(ocr.ocr))

print("\n--- PaddleOCR.predict signature ---")
# PaddleOCR might not have a predict method directly, it might be inherited or inside the ocr method
try:
    print(inspect.signature(ocr.predict))
except AttributeError:
    print("PaddleOCR has no 'predict' method directly.")

# Let's see what methods are available
# print("\n--- PaddleOCR methods ---")
# print([m for m in dir(ocr) if not m.startswith('_')])

print("\n--- Attempting minimal OCR test ---")
img = np.zeros((100, 100, 3), dtype=np.uint8)

print("Test 1: ocr.ocr(img, cls=True)")
try:
    result = ocr.ocr(img, cls=True)
    print("Test 1 success")
except Exception as e:
    print(f"Test 1 failed: {e}")

print("\nTest 2: ocr.ocr(img)")
try:
    result = ocr.ocr(img)
    print("Test 2 success")
except Exception as e:
    print(f"Test 2 failed: {e}")

print("\nTest 3: ocr.ocr(img, use_angle_cls=True)")
try:
    result = ocr.ocr(img, use_angle_cls=True)
    print("Test 3 success")
except Exception as e:
    print(f"Test 3 failed: {e}")
