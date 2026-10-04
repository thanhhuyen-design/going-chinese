import cv2
import sys
import os

sys.path.append(os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')
from detector import detect_black_frames
from ocr_engine import ocr_crop

img = cv2.imread('C:/Users/user/.gemini/antigravity/scratch/chinese-vocab-web/static/test_samples/sample_lesson_01.png')
crops = detect_black_frames(img)

debug_dir = 'C:/Users/user/.gemini/antigravity/scratch/debug_crops'
os.makedirs(debug_dir, exist_ok=True)

for i, c in enumerate(crops):
    crop_path = os.path.join(debug_dir, f'crop_{i+1}.png')
    cv2.imwrite(crop_path, c['crop_bgr'])
    res = ocr_crop(c['crop_bgr'])
    print(f"Crop {i+1} saved to {crop_path}: OCR = '{res['text']}', conf = {res['confidence']}")
