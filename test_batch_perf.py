import time
import os
import glob
import urllib.request
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

BATCH_DIR = 'C:/Users/user/.gemini/antigravity/scratch/batch_100_test'
image_files = sorted(glob.glob(os.path.join(BATCH_DIR, '*.png')))[:20]  # Test 20 images first to measure rate
print(f"Testing batch upload on {len(image_files)} images...")

def process_file(file_path):
    filename = os.path.basename(file_path)
    boundary = '----BatchBoundary987'
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode('utf-8'))
    body.extend(b'Content-Type: image/png\r\n\r\n')
    body.extend(file_bytes)
    body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/process-image',
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

t0 = time.perf_counter()
results = []
dedup_vocab = {}

# Run with 4 concurrent workers (matching browser concurrency)
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_file, f): f for f in image_files}
    completed_count = 0
    for future in as_completed(futures):
        completed_count += 1
        data = future.result()
        results.append(data)
        for w in data.get('words', []):
            h = w['hanzi']
            if h not in dedup_vocab:
                dedup_vocab[h] = {
                    'pinyin': w['pinyin'],
                    'meaning': w['meaning'],
                    'count': 1
                }
            else:
                dedup_vocab[h]['count'] += 1

t1 = time.perf_counter()
total_time = t1 - t0

print(f"\n--- Batch Benchmark Results ---")
print(f"Total images processed: {len(image_files)}")
print(f"Elapsed time: {total_time:.2f} seconds")
print(f"Average speed: {total_time / len(image_files):.2f}s per image ({len(image_files) / (total_time / 60):.1f} images/min)")
print(f"Estimated 100 images time: {(total_time / len(image_files)) * 100:.1f} seconds")
print(f"Total vocabulary detections: {sum(v['count'] for v in dedup_vocab.values())}")
print(f"Unique vocabulary words (after deduplication): {len(dedup_vocab)}")
print(f"\nDeduplicated Final Vocabulary List:")
for h, info in sorted(dedup_vocab.items(), key=lambda x: x[1]['pinyin']):
    print(f"  {info['pinyin']} — {info['meaning']} (found {info['count']} times)")
