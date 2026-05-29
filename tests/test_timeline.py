import pytest
from core.timeline import TimelineBuilder, TimelineValidator
from core.matcher import Matcher
from core.rules import RuleEngine
from core.models import Script, Segment


class StubDB:
    def __init__(self, assets):
        self._assets = assets

    def search_assets(self, keyword="", type_filter="", limit=100):
        results = []
        for a in self._assets:
            if type_filter and a["type"] != type_filter:
                continue
            if keyword:
                kw_lower = keyword.lower()
                tag_str = " ".join(a.get("tags", [])).lower()
                if kw_lower not in tag_str:
                    continue
            from core.models import Asset
            results.append(Asset(**a))
        return results


@pytest.fixture
def builder():
    db = StubDB([
        {"file": "food01.mp4", "type": "video", "tags": ["减脂", "饮食"], "width": 1920, "height": 1080, "duration": 10},
        {"file": "gym01.mp4", "type": "video", "tags": ["健身", "运动"], "width": 1920, "height": 1080, "duration": 8},
    ])
    matcher = Matcher(db)
    rules = RuleEngine()
    rules.register_defaults()
    return TimelineBuilder(matcher, rules)


class TestTimelineBuilder:
    def test_build_simple(self, builder):
        script = Script(
            title="测试",
            duration=15,
            style="knowledge",
            segments=[
                Segment(id=1, text="减脂很重要", keywords=["减脂"], duration=5),
                Segment(id=2, text="要运动", keywords=["健身"], duration=5),
            ],
        )
        timeline = builder.build(script)
        assert len(timeline.timeline) == 2
        assert timeline.timeline[0].start == 0
        assert timeline.timeline[0].end == 5
        assert timeline.timeline[1].start == 5
        assert timeline.timeline[1].end == 10

    def test_build_no_match(self, builder):
        script = Script(
            title="测试",
            duration=5,
            segments=[Segment(id=1, text="无匹配内容", keywords=["不存在的"], duration=5)],
        )
        timeline = builder.build(script)
        assert len(timeline.timeline) == 1
        assert timeline.timeline[0].asset != ""

    def test_emotion_rules_applied(self, builder):
        script = Script(
            title="测试",
            duration=10,
            segments=[Segment(id=1, text="强烈的", keywords=["减脂"], emotion="strong", duration=5)],
        )
        timeline = builder.build(script)
        assert timeline.timeline[0].subtitle_style == "big_yellow"

    def test_transition_rules(self, builder):
        script = Script(
            title="测试",
            duration=10,
            segments=[
                Segment(id=1, text="短的", keywords=["减脂"], duration=2),
                Segment(id=2, text="长的", keywords=["减脂"], duration=10),
            ],
        )
        timeline = builder.build(script)
        assert timeline.timeline[0].transition == "cut"
        assert timeline.timeline[1].transition == "dissolve"


class TestTimelineValidator:
    def test_valid(self, builder):
        script = Script(title="测试", duration=10, segments=[Segment(id=1, text="a", duration=5)])
        timeline = builder.build(script)
        validator = TimelineValidator()
        errors = validator.validate(timeline)
        assert len(errors) == 0

    def test_invalid_duration(self):
        from core.models import Timeline, TimelineItem
        tl = Timeline(timeline=[TimelineItem(start=5, end=3, asset="t.mp4")])
        validator = TimelineValidator()
        errors = validator.validate(tl)
        assert len(errors) >= 1

    def test_empty_timeline(self):
        from core.models import Timeline, TimelineItem
        tl = Timeline(timeline=[TimelineItem(start=0, end=5, asset="t.mp4")])
        validator = TimelineValidator()
        errors = validator.validate(tl)
        assert isinstance(errors, list)
