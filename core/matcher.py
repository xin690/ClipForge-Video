import re
from typing import Optional
from core.database import Database
from core.models import Asset


TONE_MAP: dict[str, set[str]] = {
    "normal": {"neutral", "natural", "daily", "indoor"},
    "strong": {"dynamic", "contrast", "bold", "bright", "red", "orange"},
    "happy": {"bright", "warm", "sunny", "colorful", "yellow", "green"},
    "sad": {"dark", "blue", "calm", "moody", "rain", "gray"},
    "calm": {"soft", "blue", "pastel", "nature", "sky", "water"},
}


class Matcher:
    def __init__(self, database: Database):
        self.db = database
        self._synonyms: dict[str, list[str]] = {}

    def load_synonyms(self, synonyms: dict[str, list[str]]):
        self._synonyms = {k.lower(): [s.lower() for s in v] for k, v in synonyms.items()}

    def match(
        self,
        text: str,
        keywords: list[str],
        top_k: int = 3,
        asset_type: str = "video",
        emotion: str = "normal",
        prev_asset: Optional[Asset] = None,
    ) -> list[tuple[Asset, float]]:
        all_keywords = self._extract_keywords(text, keywords)
        if not all_keywords:
            return []

        candidates = self.db.search_assets(type_filter=asset_type, limit=100)
        scored: list[tuple[Asset, float]] = []

        for asset in candidates:
            kw_score = self._keyword_score(asset, all_keywords)
            if kw_score <= 0:
                continue
            tone_score = self._emotion_tone_score(asset, emotion)
            div_score = self._diversity_score(asset, prev_asset, all_keywords)
            total = kw_score * 50.0 + tone_score * 30.0 + div_score * 20.0
            scored.append((asset, total))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def match_bgm(self, style: str = "knowledge", top_k: int = 1) -> list[Asset]:
        candidates = self.db.search_assets(type_filter="bgm", limit=50)

        style_keywords = {
            "knowledge": ["知识", "学习", "科普", "教育", "轻快", "nature", "ambient", "documentary", "cinematic"],
            "news": ["新闻", "资讯", "严肃", "快速", "news", "upbeat", "corporate"],
            "entertainment": ["娱乐", "欢快", "轻松", "fun", "happy", "upbeat", "pop"],
            "commerce": ["商业", "电商", "促销", "commercial", "corporate", "upbeat", "promo"],
        }

        kw = style_keywords.get(style, [])
        scored = []
        for asset in candidates:
            score = self._keyword_score(asset, kw)
            if score > 0:
                scored.append((asset, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [asset for asset, _ in scored[:top_k]]

    def _extract_keywords(self, text: str, keywords: list[str]) -> list[str]:
        result = set()
        for kw in keywords:
            result.add(kw.lower())

        text_keywords = re.findall(r"[\w\u4e00-\u9fff]+", text)
        for w in text_keywords:
            if len(w) > 1:
                result.add(w.lower())

        return list(result)

    def _keyword_score(self, asset: Asset, keywords: list[str]) -> float:
        if not asset.tags:
            return 0.0

        asset_tags = set(t.lower() for t in asset.tags)
        matched = 0
        exact_count = 0

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in asset_tags:
                matched += 2.0
                exact_count += 1
            elif kw_lower in self._synonyms:
                for syn in self._synonyms[kw_lower]:
                    if syn.lower() in asset_tags:
                        matched += 1.0
                        break

        if exact_count == 0 and matched == 0:
            return 0.0

        return matched / len(keywords) if keywords else 0.0

    def _emotion_tone_score(self, asset: Asset, emotion: str) -> float:
        if not asset.tags or emotion not in TONE_MAP:
            return 0.0
        expected = TONE_MAP[emotion]
        if not expected:
            return 0.0
        asset_tags = set(t.lower() for t in asset.tags)
        hits = sum(1 for tag in asset_tags if tag in expected)
        return min(hits / len(expected), 1.0)

    def _diversity_score(self, asset: Asset, prev_asset: Optional[Asset], keywords: list[str]) -> float:
        if not prev_asset or not prev_asset.tags or not asset.tags:
            return 0.5
        prev_tags = set(t.lower() for t in prev_asset.tags)
        cur_tags = set(t.lower() for t in asset.tags)
        overlap = len(prev_tags & cur_tags)
        if overlap == 0:
            return 1.0
        if overlap >= 3:
            return 0.0
        return max(0.0, 1.0 - overlap / 3.0)
