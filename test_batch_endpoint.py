import urllib.request
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

boundary = '----TestBatchBoundary789'
SAMPLES_DIR = 'C:/Users/user/.gemini/antigravity/scratch/chinese-vocab-web/static/test_samples'
sample_files = ['sample_lesson_01.png', 'sample_lesson_02.png', 'sample_lesson_03.png']

body = bytearray()
for fname in sample_files:
    fpath = os.path.join(SAMPLES_DIR, fname)
    with open(fpath, 'rb') as f:
        file_bytes = f.read()
    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="files"; filename="{fname}"\r\n'.encode('utf-8'))
    body.extend(b'Content-Type: image/png\r\n\r\n')
    body.extend(file_bytes)
    body.extend(b'\r\n')
body.extend(f'--{boundary}--\r\n'.encode('utf-8'))

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/process-batch',
    data=bytes(body),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))

print("Batch endpoint response status: 200 OK")
print(f"Processed batch size: {data['batch_size']}")
total_words = 0
for res in data['results']:
    print(f"  File: {res['filename']} - Status: {res['status']} ({res['box_count']} words)")
    total_words += res['box_count']
print(f"Total words extracted across batch: {total_words}")
