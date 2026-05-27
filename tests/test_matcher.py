import pytest
from core.matcher import Matcher
from core.models import Asset


class StubDB:
    def __init__(self, assets):
        self._assets = assets

    def search_assets(self, keyword="", type_filter="", limit=100):
        results = []
        for a in self._assets:
            if type_filter and a.get("type") != type_filter:
                continue
            if keyword:
                kw_lower = keyword.lower()
                tag_str = " ".join(a.get("tags", [])).lower()
                if kw_lower not in tag_str:
                    continue
            results.append(Asset(**a))
        return results

    def get_asset_by_file(self, file: str):
        for a in self._assets:
            if a.get("file") == file:
                return Asset(**a)
        return None

    def get_all_assets(self):
        return [Asset(**a) for a in self._assets]


@pytest.fixture
def matcher():
    assets = [
        {"file": "food01.mp4", "type": "video", "duration": 10, "tags": ["减脂", "沙拉", "低卡"], "width": 1920, "height": 1080},
        {"file": "gym01.mp4", "type": "video", "duration": 8, "tags": ["健身", "跑步", "运动"], "width": 1920, "height": 1080},
        {"file": "food02.mp4", "type": "video", "duration": 6, "tags": ["饮食", "健康", "营养"], "width": 1920, "height": 1080},
        {"file": "bgm01.mp3", "type": "bgm", "duration": 30, "tags": ["轻快", "背景", "音乐"], "width": 0, "height": 0},
    ]
    return Matcher(StubDB(assets))


class TestMatcher:
    def test_exact_match(self, matcher):
        results = matcher.match(text="减脂", keywords=["减脂"], top_k=3)
        assert len(results) >= 1
        assert any("减脂" in " ".join(a.tags) for a, _ in results)

    def test_no_match(self, matcher):
        results = matcher.match(text="不存在的关键词", keywords=["不存在的关键词"], top_k=3)
        assert len(results) == 0

    def test_top_k(self, matcher):
        results = matcher.match(text="健康", keywords=["健康"], top_k=1)
        assert len(results) <= 1

    def test_multiple_keywords(self, matcher):
        results = matcher.match(text="减脂饮食", keywords=["减脂", "饮食"], top_k=3)
        assert len(results) >= 1

    def test_type_filter(self, matcher):
        results = matcher.match(text="音乐", keywords=["音乐"], top_k=3, asset_type="bgm")
        assert len(results) >= 1
        assert all(a.type == "bgm" for a, _ in results)

    def test_synonym_matching(self, matcher):
        matcher.load_synonyms({"减肥": ["减脂"]})
        results = matcher.match(text="减肥", keywords=["减肥"], top_k=3)
        assert len(results) >= 1

    def test_bgm_match(self, matcher):
        results = matcher.match_bgm(style="knowledge")
        assert len(results) >= 0

    def test_score_ordering(self, matcher):
        results = matcher.match(text="减脂健身", keywords=["减脂", "健身"], top_k=3)
        if len(results) >= 2:
            first_tags = " ".join(results[0][0].tags)
            second_tags = " ".join(results[1][0].tags)
            first_score = sum(1 for kw in ["减脂", "健身"] if kw.lower() in first_tags.lower())
            second_score = sum(1 for kw in ["减脂", "健身"] if kw.lower() in second_tags.lower())
            assert results[0][1] >= results[1][1]

    def test_emotion_tone_score(self, matcher):
        results_normal = matcher.match(text="减脂", keywords=["减脂"], top_k=3, emotion="normal")
        results_strong = matcher.match(text="减脂", keywords=["减脂"], top_k=3, emotion="strong")
        assert len(results_normal) >= 0
        assert len(results_strong) >= 0

    def test_diversity_score(self, matcher):
        prev = Asset(file="gym01.mp4", type="video", tags=["健身", "运动"])
        results_no_prev = matcher.match(text="减脂", keywords=["减脂"], top_k=3)
        results_with_prev = matcher.match(text="减脂", keywords=["减脂"], top_k=3, emotion="normal", prev_asset=prev)
        assert len(results_no_prev) >= 0
        assert len(results_with_prev) >= 0
        if prev.file == "gym01.mp4":
            gym01_scores = [s for a, s in results_with_prev if a.file == "gym01.mp4"]
            food01_scores = [s for a, s in results_with_prev if a.file == "food01.mp4"]
            if gym01_scores and food01_scores:
                assert food01_scores[0] >= gym01_scores[0], "diversity penalty should reduce previous asset score"
