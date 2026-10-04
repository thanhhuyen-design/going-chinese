"""
translator.py - Dịch nghĩa tiếng Trung sang tiếng Việt tự nhiên và chính xác.
Kết hợp:
1. Từ điển ngoại tuyến (offline dictionary) tốc độ tức thì.
2. Bộ phân tích ghép từ thông minh (smart compound resolution).
3. Fallback dịch trực tuyến tốc độ cao và tự động lưu cache vĩnh viễn.
"""

import os
import re
import json
import urllib.request
import urllib.parse
from typing import Dict, Optional

DICT_PATH = os.path.join(os.path.dirname(__file__), "dict_data.json")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "vocab_cache.json")

# In-memory dictionary
_dict: Dict[str, str] = {}
_cache: Dict[str, str] = {}


def init_translator():
    global _dict, _cache
    if not _dict and os.path.exists(DICT_PATH):
        try:
            with open(DICT_PATH, "r", encoding="utf-8") as f:
                _dict = json.load(f)
        except Exception as e:
            print("Error loading dict_data.json:", e)

    if not _cache and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}


def save_cache():
    global _cache
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving vocab_cache.json:", e)


def translate_online(chinese_text: str, timeout: float = 2.0) -> Optional[str]:
    """Dịch tự động qua API nhẹ khi từ chưa có trong từ điển"""
    try:
        encoded = urllib.parse.quote(chinese_text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=vi&dt=t&q={encoded}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data and data[0] and data[0][0] and data[0][0][0]:
                trans = data[0][0][0].strip().lower()
                return trans
    except Exception:
        pass
    return None


def get_vietnamese_meaning(chinese_text: str) -> str:
    """
    Trả về nghĩa tiếng Việt tự nhiên và chuẩn xác cho từ/cụm từ tiếng Trung.
    """
    if not chinese_text:
        return ""

    init_translator()
    word = chinese_text.strip()

    # 1. Tra từ điển offline chuẩn
    if word in _dict:
        return _dict[word]

    # 2. Tra trong bộ nhớ cache
    if word in _cache:
        return _cache[word]

    # 3. Phân tách và ghép nghĩa các từ quen thuộc nếu là cụm ghép
    # Ví dụ: 买房子 -> 买 (mua) + 房子 (nhà) -> mua nhà
    if len(word) >= 3:
        for i in range(1, len(word)):
            prefix = word[:i]
            suffix = word[i:]
            if prefix in _dict and suffix in _dict:
                combined = f"{_dict[prefix]} {_dict[suffix]}".lower()
                _cache[word] = combined
                save_cache()
                return combined

    # 4. Tra dịch online và lưu cache
    online_res = translate_online(word)
    if online_res:
        # Làm sạch kết quả
        cleaned = online_res.strip()
        _cache[word] = cleaned
        save_cache()
        return cleaned

    # 5. Nếu không kết nối được và không có từ điển, trả về nhãn để người dùng điền
    return "đang cập nhật nghĩa"


def update_custom_meaning(chinese_text: str, custom_meaning: str):
    """Cập nhật nghĩa tùy chỉnh khi người dùng chỉnh sửa trên giao diện"""
    init_translator()
    word = chinese_text.strip()
    meaning = custom_meaning.strip()
    _cache[word] = meaning
    save_cache()


if __name__ == '__main__':
    tests = ['你好', '学习', '喜欢', '环境', '解释', '买房子']
    for t in tests:
        print(f"{t} -> {get_vietnamese_meaning(t)}")
