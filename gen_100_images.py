"""
Generate 100 test images simulating textbook vocabulary pages to test batch OCR performance.
"""
import os
import shutil

SAMPLES_DIR = 'C:/Users/user/.gemini/antigravity/scratch/chinese-vocab-web/static/test_samples'
BATCH_DIR = 'C:/Users/user/.gemini/antigravity/scratch/batch_100_test'
os.makedirs(BATCH_DIR, exist_ok=True)

source_samples = [
    os.path.join(SAMPLES_DIR, 'sample_lesson_01.png'),
    os.path.join(SAMPLES_DIR, 'sample_lesson_02.png'),
    os.path.join(SAMPLES_DIR, 'sample_lesson_03.png')
]

for i in range(1, 101):
    src = source_samples[(i - 1) % len(source_samples)]
    dst = os.path.join(BATCH_DIR, f'page_{i:03d}.png')
    shutil.copyfile(src, dst)

print(f"Generated 100 test images in {BATCH_DIR}")
