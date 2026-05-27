import pytest
from core.rules import (
    RuleEngine, SubtitleStyleRule, TransitionRule, CameraRule
)


@pytest.fixture
def engine():
    engine = RuleEngine()
    engine.register_defaults()
    return engine


class TestRules:
    def test_subtitle_style_normal(self, engine):
        result = engine.execute({"emotion": "normal"})
        assert "subtitle" in result
        assert result["subtitle"]["style"] == "normal"

    def test_subtitle_style_strong(self, engine):
        result = engine.execute({"emotion": "strong"})
        assert result["subtitle"]["style"] == "big_yellow"
        assert result["subtitle"]["font_size"] == 48

    def test_subtitle_style_sad(self, engine):
        result = engine.execute({"emotion": "sad"})
        assert result["subtitle"]["style"] == "soft_white"

    def test_subtitle_style_happy(self, engine):
        result = engine.execute({"emotion": "happy"})
        assert result["subtitle"]["style"] == "bold"

    def test_transition_cut(self, engine):
        result = engine.execute({"duration": 2})
        assert result["transition"] == "cut"

    def test_transition_fade(self, engine):
        result = engine.execute({"duration": 5})
        assert result["transition"] == "fade"

    def test_transition_slide(self, engine):
        result = engine.execute({"duration": 10})
        assert result["transition"] == "slide"

    def test_camera_knowledge(self, engine):
        result = engine.execute({"style": "knowledge"})
        assert result["camera"] == "slow_zoom"

    def test_camera_news(self, engine):
        result = engine.execute({"style": "news"})
        assert result["camera"] == "static"

    def test_camera_entertainment(self, engine):
        result = engine.execute({"style": "entertainment"})
        assert result["camera"] == "pan"

    def test_all_rules_combined(self, engine):
        result = engine.execute({
            "emotion": "strong",
            "duration": 7,
            "style": "knowledge",
        })
        assert result["subtitle"]["style"] == "big_yellow"
        assert result["transition"] == "fade"
        assert result["camera"] == "slow_zoom"

    def test_empty_context(self, engine):
        result = engine.execute({})
        assert "subtitle" in result
        assert "transition" in result
        assert "camera" in result

    def test_rule_priority(self):
        engine = RuleEngine()
        class LowRule:
            name = "low"
            priority = 1
            def apply(self, ctx):
                return {"test": "low"}
        class HighRule:
            name = "high"
            priority = 10
            def apply(self, ctx):
                return {"test": "high"}
        engine.register(HighRule())
        engine.register(LowRule())
        result = engine.execute({})
        assert result["test"] == "high"
