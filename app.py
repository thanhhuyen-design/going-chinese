"""
app.py - FastAPI Backend cho Website Học Từ Vựng Tiếng Trung Qua Ảnh
Hỗ trợ upload hàng trăm ảnh cùng lúc, xử lý đa luồng song song, OCR khung đen, Pinyin Unicode và dịch tiếng Việt.
"""

import os
import io
import cv2
import uuid
import base64
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from detector import detect_black_frames
from ocr_engine import ocr_crop, get_ocr_engine
from pinyin_engine import convert_to_pinyin
from translator import get_vietnamese_meaning, update_custom_meaning, init_translator

app = FastAPI(title="Hán Tự Khung Đen - Học Từ Vựng Tiếng Trung Tốc Độ Cao")

# Cho phép CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEST_SAMPLES_DIR = os.path.join(STATIC_DIR, "test_samples")
os.makedirs(TEST_SAMPLES_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup_event():
    # Warm up dictionary and OCR engine on startup
    init_translator()
    get_ocr_engine()
    # Tự động tạo ảnh mẫu thử nghiệm nếu chưa có
    generate_demo_samples_if_missing()


def crop_to_base64_jpeg(crop_bgr: np.ndarray, max_dim: int = 160) -> str:
    """Chuyển ảnh crop sang chuỗi base64 jpeg nhỏ gọn để hiển thị xem trước trực tiếp trên web"""
    if crop_bgr is None or crop_bgr.size == 0:
        return ""
    try:
        h, w = crop_bgr.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            resized = cv2.resize(crop_bgr, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
        else:
            resized = crop_bgr
        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
    except Exception:
        return ""


class RetranslateRequest(BaseModel):
    hanzi: str


class UpdateMeaningRequest(BaseModel):
    hanzi: str
    meaning: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Giao diện đang được khởi động...</h3>")


@app.post("/api/process-image")
async def process_single_image(file: UploadFile = File(...)):
    """
    Xử lý nhận diện 1 ảnh:
    1. Đọc ảnh từ binary
    2. Nhận diện các khung viền màu đen (loại bỏ toàn bộ câu/đoạn văn bên ngoài)
    3. OCR chữ Hán trong từng khung
    4. Sinh Pinyin Unicode có dấu thanh chuẩn
    5. Tra dịch nghĩa tiếng Việt tự nhiên
    """
    try:
        content = await file.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": f"Không thể giải mã file ảnh {file.filename}. Vui lòng kiểm tra lại định dạng ảnh."
            })

        # Bước 1: Phát hiện các khung màu đen
        boxes = detect_black_frames(img)

        extracted_words = []
        for b in boxes:
            crop_bgr = b['crop_bgr']
            ocr_res = ocr_crop(crop_bgr)
            hanzi = ocr_res['text']

            # Bỏ qua nếu khung rỗng không có chữ
            if not hanzi:
                continue

            pinyin = convert_to_pinyin(hanzi)
            meaning = get_vietnamese_meaning(hanzi)
            thumb_b64 = crop_to_base64_jpeg(crop_bgr)

            extracted_words.append({
                "id": str(uuid.uuid4()),
                "hanzi": hanzi,
                "pinyin": pinyin,
                "meaning": meaning,
                "confidence": ocr_res['confidence'],
                "needs_review": ocr_res['needs_review'],
                "crop_preview": thumb_b64,
                "box": {
                    "x": b['x'],
                    "y": b['y'],
                    "w": b['w'],
                    "h": b['h']
                }
            })

        return {
            "filename": file.filename,
            "status": "success" if extracted_words else "no_boxes_found",
            "box_count": len(extracted_words),
            "words": extracted_words
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "filename": file.filename,
            "status": "error",
            "message": str(e),
            "words": []
        })


def _process_image_bytes(filename: str, content: bytes) -> Dict[str, Any]:
    """Hàm phụ trợ xử lý ảnh từ bytes cho đa luồng ThreadPoolExecutor"""
    try:
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"filename": filename, "status": "error", "message": "Không thể giải mã file ảnh", "words": []}

        boxes = detect_black_frames(img)
        extracted = []
        for b in boxes:
            crop_bgr = b['crop_bgr']
            ocr_res = ocr_crop(crop_bgr)
            hanzi = ocr_res['text']
            if not hanzi:
                continue
            pinyin = convert_to_pinyin(hanzi)
            meaning = get_vietnamese_meaning(hanzi)
            thumb = crop_to_base64_jpeg(crop_bgr)
            extracted.append({
                "id": str(uuid.uuid4()),
                "hanzi": hanzi,
                "pinyin": pinyin,
                "meaning": meaning,
                "confidence": ocr_res['confidence'],
                "needs_review": ocr_res['needs_review'],
                "crop_preview": thumb,
                "box": {"x": b['x'], "y": b['y'], "w": b['w'], "h": b['h']}
            })
        return {
            "filename": filename,
            "status": "success" if extracted else "no_boxes_found",
            "box_count": len(extracted),
            "words": extracted
        }
    except Exception as ex:
        return {"filename": filename, "status": "error", "message": str(ex), "words": []}


@app.post("/api/process-batch")
async def process_batch_images(files: List[UploadFile] = File(...)):
    """
    Xử lý một nhóm ảnh song song trên máy chủ bằng ThreadPoolExecutor đa luồng.
    Tận dụng tối đa 8 CPU Cores để đạt tốc độ cao nhất khi xử lý hàng trăm ảnh.
    """
    from concurrent.futures import ThreadPoolExecutor
    
    file_payloads = []
    for f in files:
        b = await f.read()
        file_payloads.append((f.filename, b))

    max_workers = min(len(file_payloads), 6)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_image_bytes, fname, data) for fname, data in file_payloads]
        for fut in futures:
            results.append(fut.result())

    return {"batch_size": len(results), "results": results}


@app.post("/api/retranslate")
async def retranslate_text(req: RetranslateRequest):
    """
    Khi người dùng sửa chữ Hán trong bảng kiểm tra chất lượng,
    API này lập tức tính toán lại Pinyin có dấu và nghĩa tiếng Việt mới.
    """
    hanzi = req.hanzi.strip()
    if not hanzi:
        return {"pinyin": "", "meaning": ""}

    pinyin = convert_to_pinyin(hanzi)
    meaning = get_vietnamese_meaning(hanzi)
    return {
        "hanzi": hanzi,
        "pinyin": pinyin,
        "meaning": meaning
    }


@app.post("/api/update-meaning")
async def update_meaning(req: UpdateMeaningRequest):
    """Lưu nghĩa tiếng Việt thủ công do người dùng tùy chỉnh"""
    update_custom_meaning(req.hanzi, req.meaning)
    return {"status": "ok", "hanzi": req.hanzi, "meaning": req.meaning}


@app.get("/api/network-info")
async def get_network_info():
    """Lấy thông tin URL công khai và URL mạng LAN để hiển thị trên giao diện"""
    tunnel_file = os.path.join(BASE_DIR, "tunnel_info.json")
    if os.path.exists(tunnel_file):
        try:
            with open(tunnel_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "local_url": "http://127.0.0.1:8000",
        "lan_url": "http://192.168.21.103:8000",
        "public_url": "https://pressed-including-lock-nothing.trycloudflare.com"
    }


@app.get("/api/demo-samples")
async def get_demo_samples():
    """Lấy danh sách các ảnh mẫu có sẵn để người dùng bấm thử nghiệm ngay"""
    samples = []
    if os.path.exists(TEST_SAMPLES_DIR):
        for fname in sorted(os.listdir(TEST_SAMPLES_DIR)):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                samples.append({
                    "name": fname,
                    "url": f"/static/test_samples/{fname}"
                })
    return {"samples": samples}


def get_cjk_font(size: int):
    """
    Tìm font chữ CJK hỗ trợ tiếng Trung trên nhiều hệ điều hành:
    - Windows: msyh.ttc, simsun.ttc, simhei.ttf
    - Linux (Render / Ubuntu / Debian / Docker): wqy-microhei, wqy-zenhei, NotoSansCJK, DroidSansFallback
    - Fallback: ImageFont.load_default()
    """
    candidate_paths = [
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        # Linux (Render, Railway, Ubuntu, Debian, Docker)
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_demo_samples_if_missing():
    """Tạo sẵn các trang ảnh mẫu chứa khung màu đen và văn bản bên ngoài để demo tức thì"""
    try:
        # Nếu các tệp mẫu đã có sẵn (được commit trong static/test_samples), không cần tạo lại
        sample_names = ["sample_lesson_01.png", "sample_lesson_02.png", "sample_lesson_03.png"]
        all_exist = all(os.path.exists(os.path.join(TEST_SAMPLES_DIR, f)) for f in sample_names)
        if all_exist:
            return

        font_large = get_cjk_font(34)
        font_mid = get_cjk_font(24)
        font_small = get_cjk_font(18)

        demo_data = [
            {
                "file": "sample_lesson_01.png",
                "title": "Bài 1: Giao tiếp thường nhật (Chỉ lấy chữ trong khung đen)",
                "outside": [
                    "例句一：你好！很高兴在这个美丽的大学遇见你。",
                    "注意：本段为课后参考阅读材料，系统必须自动忽略，不可提取。",
                    "语法提示：请同学们牢记动词与名词的搭配原则。"
                ],
                "boxes": [
                    {"text": "你好", "y": 140, "expl": "例句：你好，请问图书馆在哪里？"},
                    {"text": "学习", "y": 240, "expl": "例句：他正在大学里认真学习汉语。"},
                    {"text": "环境", "y": 340, "expl": "例句：这里的学习环境非常安静舒适。"},
                    {"text": "解释", "y": 440, "expl": "例句：请老师为我们详细解释这个词汇。"},
                    {"text": "买房子", "y": 540, "expl": "例句：他们打算结婚后在这个城市买房子。"}
                ]
            },
            {
                "file": "sample_lesson_02.png",
                "title": "Bài 2: Đời sống & Thói quen (Chỉ lấy chữ trong khung đen)",
                "outside": [
                    "课文导读：现代人的生活节奏越来越快，大家都在追求健康与平衡。",
                    "思考题：你平时的业余爱好是什么？请用中文写一段话。"
                ],
                "boxes": [
                    {"text": "喜欢", "y": 140, "expl": "例句：我非常喜欢在中国旅游和品尝美食。"},
                    {"text": "朋友", "y": 240, "expl": "例句：周末我和几个要好的朋友去公园散步。"},
                    {"text": "漂亮", "y": 340, "expl": "例句：这件衣服的设计非常漂亮，颜色很衬你。"},
                    {"text": "便宜", "y": 440, "expl": "例句：这家超市的水果不仅新鲜，而且很便宜。"},
                    {"text": "旅游", "y": 540, "expl": "例句：明年暑假我们一家人打算去云南旅游。"}
                ]
            },
            {
                "file": "sample_lesson_03.png",
                "title": "Bài 3: Công việc & Phát triển (Chỉ lấy chữ trong khung đen)",
                "outside": [
                    "职场技巧：如何在上级面前清晰表达自己的工作构想与方案。",
                    "背景知识：面试时需要着装得体，态度诚恳自然。"
                ],
                "boxes": [
                    {"text": "准备", "y": 140, "expl": "例句：面试前一定要充分准备自我介绍。"},
                    {"text": "机会", "y": 240, "expl": "例句：只要努力拼搏，总会迎来展示自我的机会。"},
                    {"text": "成功", "y": 340, "expl": "例句：经过大家的共同奋斗，这个项目取得了巨大成功。"},
                    {"text": "简单", "y": 440, "expl": "例句：这个问题看起来并不简单，需要仔细分析。"},
                    {"text": "努力", "y": 540, "expl": "例句：为了实现心中的理想，他每天都在默默努力。"}
                ]
            }
        ]

        for demo in demo_data:
            out_path = os.path.join(TEST_SAMPLES_DIR, demo["file"])
            if os.path.exists(out_path):
                continue

            img = Image.new('RGB', (950, 720), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Vẽ tiêu đề và văn bản bên ngoài (không nằm trong khung)
            draw.text((50, 30), demo["title"], font=font_mid, fill=(20, 20, 20))
            draw.line([(50, 68), (900, 68)], fill=(220, 220, 220), width=1)

            curr_y = 80
            for out_line in demo["outside"]:
                draw.text((50, curr_y), out_line, font=font_small, fill=(110, 110, 110))
                curr_y += 24

            # Vẽ từng khung màu đen và từ vựng bên trong
            for b in demo["boxes"]:
                y_box = b["y"]
                w_box = 180 if len(b["text"]) <= 2 else 240
                h_box = 75

                # Khung màu đen rõ rệt
                draw.rectangle([50, y_box, 50 + w_box, y_box + h_box], outline=(0, 0, 0), width=4)
                # Chữ Hán bên trong khung
                draw.text((75, y_box + 16), b["text"], font=font_large, fill=(0, 0, 0))
                # Câu ví dụ bên ngoài khung (phải bị bỏ qua)
                draw.text((50 + w_box + 30, y_box + 24), b["expl"], font=font_small, fill=(100, 100, 100))

            img.save(out_path)
            print("Generated demo sample:", out_path)

    except Exception as e:
        print("Error generating demo samples:", e)


if __name__ == '__main__':
    import uvicorn
    # Hỗ trợ cổng linh hoạt từ biến môi trường PORT (cần thiết cho Render, Railway, Heroku)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting server on {host}:{port}...")
    uvicorn.run("app:app", host=host, port=port, reload=False)

