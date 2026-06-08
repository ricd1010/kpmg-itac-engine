import paddleocr
from paddleocr import PaddleOCR
import numpy as np
import warnings

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings("ignore", category=DeprecationWarning)

print(f"PaddleOCR version: {paddleocr.__version__}")

# Initialize OCR engine
# Note: use_angle_cls is also deprecated, using use_textline_orientation if possible
# But constructor might still take it. Let's check constructor signature too.
import inspect
print("\n--- PaddleOCR.__init__ signature ---")
print(inspect.signature(PaddleOCR.__init__))

ocr = PaddleOCR(lang='ch')

img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

print("\n--- Testing predict with use_textline_orientation=True ---")
try:
    # Based on our inspection, use_textline_orientation is the replacement for cls
    result = ocr.predict(img, use_textline_orientation=True)
    print("predict(img, use_textline_orientation=True) success")
    # print(result)
except Exception as e:
    print(f"predict(img, use_textline_orientation=True) failed: {e}")

print("\n--- Testing ocr with use_textline_orientation=True ---")
try:
    result = ocr.ocr(img, use_textline_orientation=True)
    print("ocr(img, use_textline_orientation=True) success")
except Exception as e:
    print(f"ocr(img, use_textline_orientation=True) failed: {e}")

print("\n--- Testing predict without extra args ---")
try:
    result = ocr.predict(img)
    print("predict(img) success")
except Exception as e:
    print(f"predict(img) failed: {e}")
