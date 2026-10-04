import urllib.request
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

boundary = '----TestBoundary123456'
img_path = 'C:/Users/user/.gemini/antigravity/scratch/test_page.png'

with open(img_path, 'rb') as f:
    file_bytes = f.read()

body = bytearray()
body.extend(f'--{boundary}\r\n'.encode('utf-8'))
body.extend(b'Content-Disposition: form-data; name="file"; filename="test_page.png"\r\n')
body.extend(b'Content-Type: image/png\r\n\r\n')
body.extend(file_bytes)
body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/process-image',
    data=bytes(body),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))

print('Process image response status:', data['status'])
print(f'Total black box words found: {len(data["words"])}')
for w in data['words']:
    print(f"  {w['pinyin']} — {w['meaning']} (Hanzi: {w['hanzi']}, conf: {w['confidence']})")
