import paddleocr
from paddleocr import PaddleOCR
import inspect

print("--- PaddleOCR.ocr source ---")
try:
    print(inspect.getsource(PaddleOCR.ocr))
except Exception as e:
    print(f"Error getting ocr source: {e}")

print("\n--- PaddleOCR.predict source ---")
try:
    print(inspect.getsource(PaddleOCR.predict))
except Exception as e:
    print(f"Error getting predict source: {e}")
