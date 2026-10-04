import time
import cv2
import sys
import os

sys.path.append(os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

from detector import detect_black_frames
from ocr_engine import ocr_crop
from pinyin_engine import convert_to_pinyin
from translator import get_vietnamese_meaning

img = cv2.imread('C:/Users/user/.gemini/antigravity/scratch/test_page.png')

# Warm-up run
detect_black_frames(img)
ocr_crop(img[:50, :50])

print("--- Measuring warm batch speed ---")
for iteration in range(3):
    t0 = time.perf_counter()
    crops = detect_black_frames(img)
    results = []
    for c in crops:
        ocr_res = ocr_crop(c['crop_bgr'])
        txt = ocr_res['text']
        pinyin = convert_to_pinyin(txt)
        meaning = get_vietnamese_meaning(txt)
        results.append({
            'hanzi': txt,
            'pinyin': pinyin,
            'meaning': meaning,
            'conf': ocr_res['confidence']
        })
    t1 = time.perf_counter()
    print(f"Run {iteration + 1}: Processed 1 image with {len(crops)} black boxes in {(t1-t0)*1000:.1f} ms")

print("\nFinal Extracted Vocabulary:")
for r in results:
    print(f"  {r['pinyin']} — {r['meaning']} (Hanzi: {r['hanzi']}, conf: {r['conf']})")

