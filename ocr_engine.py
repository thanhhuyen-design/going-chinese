"""
ocr_engine.py - Nhận diện chữ tiếng Trung bên trong từng vùng khung ảnh cắt ra.
Sử dụng RapidOCR (PP-OCRv4 ONNX) cho tốc độ cao và độ chính xác vượt trội.
"""

import re
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from typing import Dict, Any, Optional

# Khởi tạo singleton RapidOCR engine để tránh reload model nhiều lần
_engine: Optional[RapidOCR] = None


def get_ocr_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        _engine = RapidOCR()
    return _engine


def preprocess_crop(crop_bgr: np.ndarray) -> np.ndarray:
    """
    Tiền xử lý ảnh vùng cắt:
    - Thêm viền trắng (padding) xung quanh để tránh nét chữ chạm sát mép viền,
      giúp mô hình DBNet của RapidOCR nhận diện chữ Hán chính xác tuyệt đối.
    - Phóng to nếu ảnh quá nhỏ để nét chữ sắc nét.
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return crop_bgr

    # Thêm viền trắng 14px trên dưới, 18px trái phải
    padded = cv2.copyMakeBorder(crop_bgr, 14, 14, 18, 18, cv2.BORDER_CONSTANT, value=[255, 255, 255])

    h, w = padded.shape[:2]
    # Nếu chiều cao < 55px, upscale nhẹ lên 55-64px
    if h < 55:
        scale = 55.0 / float(h)
        new_w = max(int(w * scale), 30)
        new_h = 55
        padded = cv2.resize(padded, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    return padded


def clean_chinese_text(raw_text: str) -> str:
    """
    Làm sạch kết quả OCR:
    - Loại bỏ dấu ngoặc, ký tự rác, dấu chấm, gạch ngang thừa nếu OCR bắt nhầm viền.
    - Giữ lại các chữ Hán và dấu cách hợp lý giữa các từ.
    """
    if not raw_text:
        return ""
        
    text = raw_text.strip()
    
    # Xóa các ký tự viền như |, _, -, ~, `, ', ", [, ], (, ), 【, 】, 。, 、, ；, ：
    text = re.sub(r'^[\|_\-\~`\'\"\[\]\(\)【】。、；：\s]+', '', text)
    text = re.sub(r'[\|_\-\~`\'\"\[\]\(\)【】。、；：\s]+$', '', text)
    text = re.sub(r'[\r\n\t]+', ' ', text)
    
    # Loại bỏ các ký tự rác đơn lẻ (ví dụ 1 dấu gạch | sót lại)
    text = text.strip()
    return text


def ocr_crop(crop_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Nhận diện chữ Hán trong vùng ảnh cắt.
    Trả về:
    - text: Chữ Hán đã làm sạch
    - confidence: Độ tin cậy (0.0 - 1.0)
    - needs_review: True nếu độ tin cậy < 0.85 hoặc chuỗi quá ngắn/rỗng
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return {
            'text': '',
            'confidence': 0.0,
            'needs_review': True,
            'raw_results': []
        }

    engine = get_ocr_engine()
    processed_crop = preprocess_crop(crop_bgr)
    
    try:
        ocr_result, elapse = engine(processed_crop)
    except Exception as e:
        return {
            'text': '',
            'confidence': 0.0,
            'needs_review': True,
            'error': str(e)
        }

    if not ocr_result:
        # Thử lại với grayscale + Otsu binarization nếu ảnh gốc có nền phức tạp
        try:
            gray = cv2.cvtColor(processed_crop, cv2.COLOR_BGR2GRAY)
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            otsu_bgr = cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)
            ocr_result, _ = engine(otsu_bgr)
        except Exception:
            pass

    if not ocr_result:
        return {
            'text': '',
            'confidence': 0.0,
            'needs_review': True,
            'raw_results': []
        }

    # Tổng hợp các đoạn chữ nhận diện được trong khung
    recognized_parts = []
    confs = []
    
    for item in ocr_result:
        # item format: [box_points, text, confidence]
        t = item[1].strip()
        c = float(item[2])
        if t:
            recognized_parts.append(t)
            confs.append(c)

    full_text = " ".join(recognized_parts)
    cleaned_text = clean_chinese_text(full_text)
    avg_conf = float(np.mean(confs)) if confs else 0.0

    # Tiêu chí đánh dấu cần kiểm tra:
    # 1. Độ tin cậy < 0.85
    # 2. Không chứa ký tự chữ Hán nào
    # 3. Chuỗi rỗng
    has_hanzi = bool(re.search(r'[\u4e00-\u9fff]', cleaned_text))
    needs_review = (avg_conf < 0.85) or (not has_hanzi) or (len(cleaned_text) == 0)

    return {
        'text': cleaned_text,
        'confidence': round(avg_conf, 3),
        'needs_review': needs_review,
        'has_hanzi': has_hanzi
    }
