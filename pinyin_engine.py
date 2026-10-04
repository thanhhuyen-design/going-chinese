"""
pinyin_engine.py - Bộ chuyển đổi Pinyin có dấu thanh Unicode chuẩn (Hanyu Pinyin Zhengcifa).
Đảm bảo chuẩn xác dấu thanh 1-4, âm ü (ǖ, ǘ, ǚ, ǜ), phân tách âm tiết hợp lý.
"""

import re
import jieba
import pypinyin
from typing import List, Dict

# Từ điển Pinyin chuẩn hóa cho các cụm từ đặc biệt hoặc đa âm tiết thông dụng
CUSTOM_PINYIN_OVERRIDES: Dict[str, str] = {
    '你好': 'nǐ hǎo',
    '您好': 'nín hǎo',
    '学习': 'xuéxí',
    '喜欢': 'xǐhuan',
    '环境': 'huánjìng',
    '解释': 'jiěshì',
    '买房子': 'mǎi fángzi',
    '对不起': 'duìbuqǐ',
    '没关系': 'méi guānxi',
    '谢谢': 'xièxie',
    '不客气': 'bú kèqi',
    '再见': 'zàijiàn',
    '什么': 'shénme',
    '怎么': 'zěnme',
    '怎么样': 'zěnmeyàng',
    '为什么': 'wèishénme',
    '认识': 'rènshi',
    '高兴': 'gāoxìng',
    '舒服': 'shūfu',
    '漂亮': 'piàoliang',
    '便宜': 'piányi',
    '东西': 'dōngxi',
    '清楚': 'qīngchu',
    '明白': 'míngbai',
    '告诉': 'gàosu',
    '朋友': 'péngyou',
    '学生': 'xuésheng',
    '老师': 'lǎoshī',
    '医生': 'yīshēng',
    '护士': 'hùshi',
}

# Đăng ký một số cụm từ thông dụng vào jieba để phân tách ngữ pháp chuẩn
CUSTOM_WORDS = [
    '买房子', '做作业', '看电影', '听音乐', '喝茶', '吃饭', '打篮球',
    '开玩笑', '谈恋爱', '找工作', '去旅游', '坐飞机', '骑自行车'
]
for w in CUSTOM_WORDS:
    jieba.add_word(w)


def get_syllable_pinyin(char: str) -> str:
    """Lấy pinyin có dấu thanh chuẩn cho một ký tự Hán"""
    p = pypinyin.lazy_pinyin(char, style=pypinyin.Style.TONE, neutral_tone_with_five=False)
    if p and p[0]:
        val = p[0].strip()
        # Chuyển đổi v -> ü nếu có
        val = val.replace('v', 'ü')
        return val
    return char


def convert_to_pinyin(chinese_text: str) -> str:
    """
    Chuyển đổi chuỗi tiếng Trung sang Hanyu Pinyin có dấu thanh Unicode chuẩn.
    Tuân thủ quy tắc chính tả Pinyin:
    - Từ ghép liền (xuéxí, huánjìng, jiěshì)
    - Cụm từ phân cách dấu cách (mǎi fángzi, nǐ hǎo)
    - Dấu thanh Unicode chính xác trên nguyên âm
    - ü: ǖ, ǘ, ǚ, ǜ
    """
    if not chinese_text:
        return ""
        
    text = chinese_text.strip()
    
    # Kiểm tra bảng đè chính xác
    if text in CUSTOM_PINYIN_OVERRIDES:
        return CUSTOM_PINYIN_OVERRIDES[text]

    # Phân đoạn từ vựng bằng jieba
    segments = jieba.lcut(text)
    
    pinyin_segments = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
            
        # Nếu đoạn nằm trong bảng đè
        if seg in CUSTOM_PINYIN_OVERRIDES:
            pinyin_segments.append(CUSTOM_PINYIN_OVERRIDES[seg])
            continue

        # Kiểm tra cụm động-tân (ví dụ: 买房子 -> 买 + 房子 -> mǎi fángzi)
        if len(seg) == 3 and not re.search(r'[^\u4e00-\u9fff]', seg):
            # Ví dụ: 买(1) + 房子(2) hoặc 打印(2) + 机(1)
            v_cut = jieba.lcut(seg, cut_all=False)
            if len(v_cut) > 1:
                sub_parts = []
                for sub in v_cut:
                    sub_p = ''.join(pypinyin.lazy_pinyin(sub, style=pypinyin.Style.TONE))
                    sub_parts.append(sub_p)
                pinyin_segments.append(' '.join(sub_parts))
                continue

        # Kiểm tra nếu là chữ Hán hoàn toàn
        is_all_hanzi = bool(re.match(r'^[\u4e00-\u9fff]+$', seg))
        if is_all_hanzi:
            # Lấy pinyin cho từng chữ trong từ ghép
            p_list = pypinyin.lazy_pinyin(seg, style=pypinyin.Style.TONE)
            # Từ ghép thì viết liền nhau (ví dụ: xuéxí, huánjìng)
            pinyin_word = ''.join(p_list)
            pinyin_segments.append(pinyin_word)
        else:
            # Ký tự số, la-tinh hoặc ký hiệu
            pinyin_segments.append(seg)

    result = " ".join(pinyin_segments)
    
    # Dọn dẹp khoảng trắng thừa
    result = re.sub(r'\s+', ' ', result).strip()
    return result


if __name__ == '__main__':
    test_cases = ['你好', '学习', '喜欢', '环境', '解释', '买房子', '绿茶', '女孩子', '旅游']
    for t in test_cases:
        print(f"{t} → {convert_to_pinyin(t)}")
