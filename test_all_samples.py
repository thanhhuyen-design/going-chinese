import urllib.request
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

for name in ['sample_lesson_01.png', 'sample_lesson_02.png', 'sample_lesson_03.png']:
    boundary = '----TestBoundary123'
    img_path = f'C:/Users/user/.gemini/antigravity/scratch/chinese-vocab-web/static/test_samples/{name}'
    with open(img_path, 'rb') as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode('utf-8'))
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
    print(f"=== {name}: {len(data['words'])} words found ===")
    for w in data['words']:
        print(f"  {w['pinyin']} — {w['meaning']} (Hanzi: {w['hanzi']})")
