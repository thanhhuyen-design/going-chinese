import urllib.request
import json
import ssl
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Allow unverified SSL context if python on windows doesn't have root ca bundle configured
ctx = ssl._create_unverified_context()

PUBLIC_URL = 'https://pressed-including-lock-nothing.trycloudflare.com'
print(f"Testing public URL: {PUBLIC_URL}")

# 1. Test GET /
try:
    req = urllib.request.Request(f"{PUBLIC_URL}/", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        html = resp.read().decode('utf-8')
        print(f"✓ GET /: HTTP {resp.status} (received {len(html)} bytes HTML)")
        assert "<title>" in html
except Exception as e:
    print(f"✗ GET / failed: {e}")
    sys.exit(1)

# 2. Test POST /api/retranslate
try:
    payload = json.dumps({"hanzi": "学习"}).encode('utf-8')
    req = urllib.request.Request(
        f"{PUBLIC_URL}/api/retranslate",
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"✓ POST /api/retranslate: {data['hanzi']} -> {data['pinyin']} — {data['meaning']}")
        assert data['pinyin'] == 'xuéxí'
except Exception as e:
    print(f"✗ POST /api/retranslate failed: {e}")
    sys.exit(1)

# 3. Test POST /api/process-image with sample_lesson_01.png
try:
    sample_path = 'C:/Users/user/.gemini/antigravity/scratch/chinese-vocab-web/static/test_samples/sample_lesson_01.png'
    boundary = '----PublicTestBoundary'
    with open(sample_path, 'rb') as f:
        img_bytes = f.read()

    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(b'Content-Disposition: form-data; name="file"; filename="sample_lesson_01.png"\r\n')
    body.extend(b'Content-Type: image/png\r\n\r\n')
    body.extend(img_bytes)
    body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    req = urllib.request.Request(
        f"{PUBLIC_URL}/api/process-image",
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f"✓ POST /api/process-image via PUBLIC URL: Status {res['status']}, found {len(res['words'])} words in black boxes:")
        for w in res['words']:
            print(f"    {w['pinyin']} — {w['meaning']}")
except Exception as e:
    print(f"✗ POST /api/process-image failed: {e}")
    sys.exit(1)

print("\n🎉 ALL PUBLIC VERIFICATION TESTS PASSED SUCCESSFULLY!")
