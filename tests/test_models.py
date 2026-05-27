import pytest
from core.models import Script, Segment, Asset, Timeline, TimelineItem


class TestModels:
    def test_segment_valid(self):
        seg = Segment(id=1, text="测试", duration=5)
        assert seg.id == 1
        assert seg.text == "测试"
        assert seg.duration == 5
        assert seg.emotion == "normal"

    def test_segment_invalid_duration(self):
        with pytest.raises(ValueError):
            Segment(id=1, text="测试", duration=0)
        with pytest.raises(ValueError):
            Segment(id=1, text="测试", duration=-1)

    def test_script_valid(self, sample_script):
        script = Script(**sample_script)
        assert len(script.segments) == 3
        assert script.style == "knowledge"
        assert script.duration == 15

    def test_script_empty_segments(self):
        with pytest.raises(ValueError):
            Script(title="test", duration=10, segments=[])

    def test_script_negative_duration(self):
        with pytest.raises(ValueError):
            Script(title="test", duration=-1, segments=[Segment(id=1, text="t")])

    def test_asset_valid(self):
        asset = Asset(file="test.mp4", type="video", tags=["测试"])
        assert asset.type == "video"
        assert asset.tags == ["测试"]

    def test_asset_invalid_type(self):
        with pytest.raises(ValueError):
            Asset(file="test.mp4", type="invalid")

    def test_timeline_item_valid(self):
        item = TimelineItem(start=0, end=5, asset="test.mp4")
        assert item.transition == "cut"
        assert item.camera == "static"

    def test_timeline_valid(self):
        item = TimelineItem(start=0, end=5, asset="test.mp4")
        tl = Timeline(timeline=[item])
        assert len(tl.timeline) == 1
        assert tl.resolution == (1920, 1080)

    def test_timeline_empty(self):
        with pytest.raises(ValueError):
            Timeline(timeline=[])
