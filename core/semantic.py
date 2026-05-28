import re

_CN_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
    "看", "好", "自己", "这", "他", "她", "它", "们", "这个", "那个",
    "可以", "因为", "所以", "但是", "而且", "如果", "虽然", "已经",
    "什么", "怎么", "为什么", "然后", "那么", "就是", "还是",
    "可能", "一定", "应该", "需要", "不是", "但是", "只是",
    "一些", "很多", "比较", "非常", "那么", "这样", "那样",
}

CATEGORY_MAP: dict[tuple[str, str], list[str]] = {
    ("knowledge", "normal"): ["abstract", "neutral", "indoor", "textbook", "whiteboard", "study"],
    ("knowledge", "strong"): ["tech", "dynamic", "contrast", "data", "blueprint", "cyber"],
    ("knowledge", "calm"):   ["nature", "forest", "ocean", "sky", "meditation", "green"],
    ("knowledge", "happy"):  ["campus", "sunny", "library", "laboratory", "colorful"],
    ("knowledge", "sad"):    ["archive", "dark", "historical", "museum", "monochrome"],

    ("news", "normal"):    ["urban", "office", "meeting", "interview", "desk"],
    ("news", "strong"):    ["crowd", "conference", "demonstration", "action", "city"],
    ("news", "calm"):      ["nature", "timelapse", "drone", "aerial", "wide"],
    ("news", "happy"):     ["festival", "celebration", "parade", "event", "colorful"],
    ("news", "sad"):       ["memorial", "hospital", "damage", "rescue", "dark"],

    ("entertainment", "normal"):  ["casual", "daily", "vlog", "street", "lifestyle"],
    ("entertainment", "strong"):  ["party", "concert", "sports", "extreme", "crowd"],
    ("entertainment", "calm"):    ["sunset", "beach", "relax", "scenery", "nature"],
    ("entertainment", "happy"):   ["colorful", "toy", "game", "funny", "animal"],
    ("entertainment", "sad"):     ["monochrome", "portrait", "alone", "night", "moody"],

    ("commerce", "normal"):    ["product", "studio", "white_bg", "showcase", "clean"],
    ("commerce", "strong"):    ["sale", "discount", "fashion", "luxury", "gold"],
    ("commerce", "calm"):      ["lifestyle", "minimal", "clean", "organic", "soft"],
    ("commerce", "happy"):     ["gift", "unboxing", "fresh", "packaging", "bright"],
    ("commerce", "sad"):       ["vintage", "rust", "bargain", "old_fashion", "gray"],
}


def extract_keywords_from_text(text: str) -> list[str]:
    chunks = re.split(r"[\u3000-\u303f\uff00-\uffef\s,.\!\?;:\"'()\n]+", text)
    keywords: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) < 2:
            continue
        if chunk.lower() in _CN_STOP_WORDS:
            continue
        cn_chars = re.findall(r"[\u4e00-\u9fff]{2,}", chunk)
        for c in cn_chars:
            if c.lower() not in _CN_STOP_WORDS:
                keywords.append(c)
                if len(c) > 2:
                    for i in range(len(c) - 2):
                        sub = c[i:i + 2]
                        if sub.lower() not in _CN_STOP_WORDS:
                            keywords.append(sub)
        en_words = re.findall(r"[a-zA-Z]{3,}", chunk)
        for w in en_words:
            if w.lower() not in _CN_STOP_WORDS:
                keywords.append(w.lower())
    return list(dict.fromkeys(keywords))


def get_category_tags(style: str, emotion: str) -> list[str]:
    key = (style, emotion)
    if key in CATEGORY_MAP:
        return list(CATEGORY_MAP[key])
    for (s, e), tags in CATEGORY_MAP.items():
        if s == style:
            return list(tags)
    return list(CATEGORY_MAP.get(("knowledge", "normal"), []))


def category_match_score(asset_tags: list[str], category_tags: list[str]) -> float:
    if not category_tags:
        return 0.0
    atags = set(t.lower() for t in asset_tags)
    hits = sum(1 for tag in category_tags if tag.lower() in atags)
    return min(hits / len(category_tags), 1.0)
