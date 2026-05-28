from core.semantic import (
    extract_keywords_from_text,
    get_category_tags,
    category_match_score,
    CATEGORY_MAP,
)


class TestExtractKeywords:

    def test_basic_chinese(self):
        kw = extract_keywords_from_text("科学研究表明，控制热量摄入比增加运动消耗更有效。")
        assert "科学" in kw or "研究" in kw or "热量" in kw or "运动" in kw

    def test_short_text(self):
        kw = extract_keywords_from_text("你好")
        assert isinstance(kw, list)

    def test_empty_text(self):
        kw = extract_keywords_from_text("")
        assert kw == []

    def test_english_words(self):
        kw = extract_keywords_from_text("AI technology is transforming the world")
        assert "technology" in kw or "transforming" in kw or "world" in kw

    def test_dedup(self):
        kw = extract_keywords_from_text("科学科学科学研究")
        assert len(kw) == len(set(kw))

    def test_stop_words_filtered(self):
        kw = extract_keywords_from_text("因为所以可以但是")
        assert "因为" not in kw
        assert "所以" not in kw


class TestCategoryMap:

    def test_known_pair(self):
        tags = get_category_tags("knowledge", "strong")
        assert isinstance(tags, list)
        assert len(tags) > 0
        assert "tech" in tags

    def test_all_pairs_have_tags(self):
        for style in ["knowledge", "news", "entertainment", "commerce"]:
            for emotion in ["normal", "strong", "calm", "happy", "sad"]:
                tags = get_category_tags(style, emotion)
                assert isinstance(tags, list), f"Missing: {style}×{emotion}"
                assert len(tags) > 0, f"Empty: {style}×{emotion}"

    def test_unknown_style_fallback(self):
        tags = get_category_tags("unknown_style", "normal")
        assert isinstance(tags, list)
        assert len(tags) > 0


class TestCategoryMatchScore:

    def test_full_match(self):
        score = category_match_score(["tech", "dynamic"], ["tech", "dynamic", "data"])
        assert score > 0.5

    def test_no_match(self):
        score = category_match_score(["food", "cooking"], ["tech", "dynamic"])
        assert score == 0.0

    def test_empty_category(self):
        score = category_match_score(["anything"], [])
        assert score == 0.0

    def test_empty_asset(self):
        score = category_match_score([], ["tech", "dynamic"])
        assert score == 0.0
