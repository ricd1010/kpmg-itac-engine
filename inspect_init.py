import paddleocr
from paddleocr import PaddleOCR
import inspect

print("--- PaddleOCR.__init__ source ---")
try:
    print(inspect.getsource(PaddleOCR.__init__))
except Exception as e:
    print(f"Error getting __init__ source: {e}")
