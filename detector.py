"""
detector.py - Module phát hiện khung màu đen (black frames / boxes) và trích xuất vùng chữ.
Tối ưu cho việc lọc bỏ văn bản bên ngoài khung (câu ví dụ, bài đọc, giải thích).
"""

import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Any


def is_box_border_dark(gray_img: np.ndarray, x: int, y: int, w: int, h: int, thickness: int = 3, threshold: int = 125) -> bool:
    """
    Kiểm tra xem 4 cạnh của khung chữ nhật có thực sự là viền màu đen/tối hay không.
    """
    img_h, img_w = gray_img.shape
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(img_w, x + w), min(img_h, y + h)
    
    if x2 - x1 < 10 or y2 - y1 < 10:
        return False
        
    box_crop = gray_img[y1:y2, x1:x2]
    ch, cw = box_crop.shape
    
    t = min(thickness, ch // 4, cw // 4)
    if t < 1:
        t = 1
        
    # Lấy 4 dải viền: trên, dưới, trái, phải
    top_border = box_crop[0:t, :]
    bottom_border = box_crop[ch-t:ch, :]
    left_border = box_crop[:, 0:t]
    right_border = box_crop[:, cw-t:cw]
    
    border_pixels = np.concatenate([
        top_border.flatten(),
        bottom_border.flatten(),
        left_border.flatten(),
        right_border.flatten()
    ])
    
    median_val = np.median(border_pixels)
    dark_ratio = np.mean(border_pixels < threshold)
    
    # Một khung màu đen chuẩn sẽ có đa số pixel trên đường viền là màu tối (< threshold)
    return dark_ratio > 0.45 or median_val < threshold


def calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Tính Intersection over Union (IoU) giữa 2 bounding box [x, y, w, h]"""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]

    denom = float(boxAArea + boxBArea - interArea)
    return interArea / denom if denom > 0 else 0.0


def deduplicate_boxes(boxes: List[Dict[str, Any]], iou_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """Loại bỏ các box trùng lặp hoặc viền lồng nhau (inner/outer contour của cùng một nét vẽ viền)"""
    if not boxes:
        return []
        
    # Ưu tiên box có diện tích phù hợp và độ rõ viền cao
    boxes = sorted(boxes, key=lambda b: (b['y'], b['x']))
    kept: List[Dict[str, Any]] = []
    
    for b in boxes:
        box_coords = (b['x'], b['y'], b['w'], b['h'])
        duplicate = False
        for k in kept:
            k_coords = (k['x'], k['y'], k['w'], k['h'])
            # Nếu IoU cao hoặc một box nằm trọn trong box kia với tỉ lệ diện tích sát nhau
            iou = calculate_iou(box_coords, k_coords)
            if iou > iou_threshold:
                duplicate = True
                break
            # Kiểm tra chứa nhau
            if (box_coords[0] >= k_coords[0] - 8 and box_coords[1] >= k_coords[1] - 8 and
                box_coords[0] + box_coords[2] <= k_coords[0] + k_coords[2] + 8 and
                box_coords[1] + box_coords[3] <= k_coords[1] + k_coords[3] + 8):
                duplicate = True
                break
        if not duplicate:
            kept.append(b)
            
    return kept


def detect_black_frames(cv_image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Nhận diện tất cả các khung màu đen chứa từ vựng trong ảnh.
    Trả về danh sách các vùng crop bên trong khung kèm tọa độ.
    """
    if cv_image is None or cv_image.size == 0:
        return []

    h_img, w_img = cv_image.shape[:2]
    total_area = h_img * w_img
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY) if len(cv_image.shape) == 3 else cv_image

    detected_boxes: List[Dict[str, Any]] = []

    # Phương pháp 1: Thresholding tìm viền đen (nét vẽ màu đen trên nền sáng)
    # Thử nhiều ngưỡng để thích ứng với ảnh scan, ảnh chụp ánh sáng khác nhau
    thresholds = [100, 130, 80]
    
    for thresh_val in thresholds:
        _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
        
        # Tìm contours với cây phân cấp
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if hierarchy is None or len(contours) == 0:
            continue
            
        hierarchy = hierarchy[0]
        
        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            rect_area = w * h
            if rect_area <= 0:
                continue
                
            # Điều kiện kích thước khung từ vựng:
            # - Không quá nhỏ (ít nhất rộng 35px, cao 18px để chứa được 1 chữ Hán)
            # - Không chiếm toàn bộ trang ảnh (> 95% diện tích)
            if w < 35 or h < 18:
                continue
            if rect_area > 0.92 * total_area:
                continue
            if w > 0.95 * w_img and h > 0.95 * h_img:
                continue
                
            extent = area / float(rect_area)
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
            
            # Khung chữ nhật thường có extent > 0.65 (tính cả bo góc nhẹ) và 4-8 đỉnh
            is_rect = extent > 0.65 or (len(approx) >= 4 and len(approx) <= 8)
            
            if not is_rect:
                continue
                
            # Kiểm tra xem đây có phải là khung viền có chứa phần tử bên trong (has_child)
            # hoặc có viền đen xung quanh
            has_child = hierarchy[i][2] != -1
            is_dark_border = is_box_border_dark(gray, x, y, w, h, thickness=4, threshold=thresh_val)
            
            # Kiểm tra xem có phải khung màu đen nền đen chữ trắng (inverted solid box)
            inner_crop_gray = gray[y+2:y+h-2, x+2:x+w-2] if h > 4 and w > 4 else gray[y:y+h, x:x+w]
            is_solid_black = False
            if inner_crop_gray.size > 0:
                is_solid_black = np.mean(inner_crop_gray < 90) > 0.60

            if (is_dark_border and (has_child or extent > 0.75)) or is_solid_black:
                detected_boxes.append({
                    'x': int(x),
                    'y': int(y),
                    'w': int(w),
                    'h': int(h),
                    'is_solid_black': is_solid_black,
                    'extent': float(extent)
                })

    # Phương pháp 2: Morphological line detector cho các khung có nét vẽ đứt đoạn
    if len(detected_boxes) == 0:
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
        _, binary = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
        
        lines_h = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_h)
        lines_v = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v)
        table_mask = cv2.add(lines_h, lines_v)
        
        cnts, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            x, y, w, h = cv2.boundingRect(cnt)
            if w >= 35 and h >= 18 and (w * h) < 0.90 * total_area:
                detected_boxes.append({
                    'x': int(x),
                    'y': int(y),
                    'w': int(w),
                    'h': int(h),
                    'is_solid_black': False,
                    'extent': 1.0
                })

    # Lọc trùng lặp các box
    unique_boxes = deduplicate_boxes(detected_boxes, iou_threshold=0.4)
    
    # Sắp xếp thứ tự tự nhiên đọc sách: từ trên xuống dưới, từ trái sang phải
    # Dùng ngưỡng hàng y_group để các từ cùng hàng được xếp trái -> phải
    def sort_key(b):
        row = b['y'] // 30
        return (row, b['x'])
        
    unique_boxes = sorted(unique_boxes, key=sort_key)
    
    # Cắt (crop) từng vùng bên trong khung
    results = []
    for idx, b in enumerate(unique_boxes):
        x, y, w, h = b['x'], b['y'], b['w'], b['h']
        
        # Thụt lề vào trong một chút (inward margin) để loại bỏ nét vẽ viền đen
        # Giúp OCR chỉ tập trung vào chữ Hán, không bị nét viền gây nhiễu
        margin_x = max(2, min(6, int(w * 0.04)))
        margin_y = max(2, min(5, int(h * 0.05)))
        
        crop_x1 = max(0, x + margin_x)
        crop_y1 = max(0, y + margin_y)
        crop_x2 = min(w_img, x + w - margin_x)
        crop_y2 = min(h_img, y + h - margin_y)
        
        if crop_x2 - crop_x1 < 10 or crop_y2 - crop_y1 < 10:
            crop_x1, crop_y1, crop_x2, crop_y2 = x, y, x + w, y + h
            
        crop_bgr = cv_image[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Nếu là solid black box (chữ trắng trên nền đen), đảo màu thành chữ đen nền trắng
        if b.get('is_solid_black', False):
            crop_bgr = cv2.bitwise_not(crop_bgr)
            
        results.append({
            'box_id': idx + 1,
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'crop_bgr': crop_bgr,
            'is_solid_black': b.get('is_solid_black', False)
        })
        
    return results
