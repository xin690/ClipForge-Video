import re
from core.synonyms import SynonymEngine

_SYN_ENGINE = SynonymEngine()

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
    ("knowledge", "normal"): ["abstract", "neutral", "indoor", "textbook", "whiteboard", "study",
                               "抽象", "中性", "室内", "课本", "白板", "学习"],
    ("knowledge", "strong"): ["tech", "dynamic", "contrast", "data", "blueprint", "cyber",
                               "科技", "动态", "对比", "数据", "蓝图", "网络"],
    ("knowledge", "calm"):   ["nature", "forest", "ocean", "sky", "meditation", "green",
                               "自然", "森林", "海洋", "天空", "冥想", "绿色"],
    ("knowledge", "happy"):  ["campus", "sunny", "library", "laboratory", "colorful",
                               "校园", "阳光", "图书馆", "实验室", "彩色"],
    ("knowledge", "sad"):    ["archive", "dark", "historical", "museum", "monochrome",
                               "档案", "黑暗", "历史", "博物馆", "黑白"],

    ("news", "normal"):    ["urban", "office", "meeting", "interview", "desk",
                             "城市", "办公室", "会议", "采访", "办公桌"],
    ("news", "strong"):    ["crowd", "conference", "demonstration", "action", "city",
                             "人群", "会议", "示威", "动作", "城市"],
    ("news", "calm"):      ["nature", "timelapse", "drone", "aerial", "wide",
                             "自然", "延时", "航拍", "鸟瞰", "广角"],
    ("news", "happy"):     ["festival", "celebration", "parade", "event", "colorful",
                             "节日", "庆祝", "游行", "活动", "彩色"],
    ("news", "sad"):       ["memorial", "hospital", "damage", "rescue", "dark",
                             "纪念", "医院", "损坏", "救援", "黑暗"],

    ("entertainment", "normal"):  ["casual", "daily", "vlog", "street", "lifestyle",
                                    "休闲", "日常", "Vlog", "街头", "生活方式"],
    ("entertainment", "strong"):  ["party", "concert", "sports", "extreme", "crowd",
                                    "派对", "演唱会", "运动", "极限", "人群"],
    ("entertainment", "calm"):    ["sunset", "beach", "relax", "scenery", "nature",
                                    "日落", "海滩", "放松", "风景", "自然"],
    ("entertainment", "happy"):   ["colorful", "toy", "game", "funny", "animal",
                                    "玩具", "游戏", "搞笑", "动物", "彩色"],
    ("entertainment", "sad"):     ["monochrome", "portrait", "alone", "night", "moody",
                                    "黑白", "肖像", "独处", "夜晚", "忧郁"],

    ("commerce", "normal"):    ["product", "studio", "white_bg", "showcase", "clean",
                                 "产品", "摄影棚", "白底", "展示", "干净"],
    ("commerce", "strong"):    ["sale", "discount", "fashion", "luxury", "gold",
                                 "促销", "折扣", "时尚", "豪华", "金色"],
    ("commerce", "calm"):      ["lifestyle", "minimal", "clean", "organic", "soft",
                                 "生活方式", "简约", "干净", "有机", "柔和"],
    ("commerce", "happy"):     ["gift", "unboxing", "fresh", "packaging", "bright",
                                 "礼物", "开箱", "新鲜", "包装", "明亮"],
    ("commerce", "sad"):       ["vintage", "rust", "bargain", "old_fashion", "gray",
                                 "复古", "生锈", "廉价", "旧式", "灰色"],
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
    atags = [t.lower() for t in asset_tags]
    hits = 0
    for cat_tag in category_tags:
        cat_lower = cat_tag.lower()
        if cat_lower in atags:
            hits += 1
        else:
            for atag in atags:
                if _SYN_ENGINE.score(cat_lower, atag) >= 0.4:
                    hits += 1
                    break
    return min(hits / len(category_tags), 1.0)
