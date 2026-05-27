import pytest
from core.qa import QAChecker, CheckResult, QASummary
from core.models import Script, Segment


class TestQAChecker:
    def _make_script(self, **overrides) -> Script:
        defaults = {
            "title": "测试",
            "duration": 15,
            "style": "knowledge",
            "voice": "zh-CN-XiaoxiaoNeural",
            "bgm": "舒缓",
            "segments": [
                Segment(id=1, text="第一段测试文案内容", keywords=["知识", "科普"], emotion="normal", duration=5),
                Segment(id=2, text="第二段测试文案内容更多", keywords=["重要", "观点"], emotion="strong", duration=6),
                Segment(id=3, text="第三段测试文案总结", keywords=["总结", "回顾"], emotion="calm", duration=4),
            ],
        }
        defaults.update(overrides)
        return Script(**defaults)

    def test_perfect_script(self):
        script = self._make_script()
        checker = QAChecker()
        summary = checker.check(script)
        assert summary.passed_all
        assert summary.failures == 0

    def test_no_bgm(self):
        script = self._make_script(bgm="")
        checker = QAChecker()
        summary = checker.check(script)
        bgm_results = [r for r in summary.results if r.name == "bgm"]
        assert len(bgm_results) == 1
        assert bgm_results[0].status == "warn"

    def test_too_few_segments(self):
        script = self._make_script(segments=[
            Segment(id=1, text="只有一段", keywords=["测试"], emotion="normal", duration=5),
        ])
        checker = QAChecker()
        summary = checker.check(script)
        seg_count = [r for r in summary.results if r.name == "segment_count"]
        assert len(seg_count) == 1
        assert seg_count[0].status == "fail"

    def test_invalid_emotion(self):
        script = self._make_script(segments=[
            Segment(id=1, text="第一段测试文案内容", keywords=["知识", "科普"], emotion="invalid", duration=5),
            Segment(id=2, text="第二段测试文案内容更多", keywords=["重要", "观点"], emotion="strong", duration=6),
            Segment(id=3, text="第三段测试文案总结", keywords=["总结", "回顾"], emotion="calm", duration=4),
        ])
        checker = QAChecker()
        summary = checker.check(script)
        emotion_results = [r for r in summary.results if r.name == "emotion"]
        assert any(r.status == "warn" for r in emotion_results)

    def test_same_emotion_adjacent(self):
        script = self._make_script(segments=[
            Segment(id=1, text="第一段测试文案内容", keywords=["知识", "科普"], emotion="normal", duration=5),
            Segment(id=2, text="第二段测试文案内容更多", keywords=["重要", "观点"], emotion="normal", duration=6),
            Segment(id=3, text="第三段测试文案总结", keywords=["总结", "回顾"], emotion="calm", duration=4),
        ])
        checker = QAChecker()
        summary = checker.check(script)
        seq_results = [r for r in summary.results if r.name == "emotion_sequence"]
        assert any(r.status == "warn" for r in seq_results)

    def test_identical_keywords_adjacent(self):
        script = self._make_script(segments=[
            Segment(id=1, text="第一段测试文案内容", keywords=["知识", "科普"], emotion="normal", duration=5),
            Segment(id=2, text="第二段测试文案内容更多", keywords=["知识", "科普"], emotion="strong", duration=6),
            Segment(id=3, text="第三段测试文案总结", keywords=["总结", "回顾"], emotion="calm", duration=4),
        ])
        checker = QAChecker()
        summary = checker.check(script)
        kw_results = [r for r in summary.results if r.name == "keyword_diversity"]
        assert any(r.status == "warn" for r in kw_results)

    def test_invalid_voice(self):
        script = self._make_script(voice="unknown-voice")
        checker = QAChecker()
        summary = checker.check(script)
        voice_results = [r for r in summary.results if r.name == "voice"]
        assert len(voice_results) == 1
        assert voice_results[0].status == "warn"

    def test_invalid_style(self):
        script = self._make_script(style="unknown")
        checker = QAChecker()
        summary = checker.check(script)
        style_results = [r for r in summary.results if r.name == "style"]
        assert len(style_results) == 1
        assert style_results[0].status == "warn"

    def test_duration_mismatch(self):
        script = self._make_script(duration=100)
        checker = QAChecker()
        summary = checker.check(script)
        dur_results = [r for r in summary.results if r.name == "duration_match"]
        assert len(dur_results) == 1
        assert dur_results[0].status == "warn"

    def test_too_few_keywords(self):
        script = self._make_script(segments=[
            Segment(id=1, text="第一段测试文案内容", keywords=["知识"], emotion="normal", duration=5),
            Segment(id=2, text="第二段测试文案内容更多", keywords=["重要", "观点"], emotion="strong", duration=6),
            Segment(id=3, text="第三段测试文案总结", keywords=["总结", "回顾"], emotion="calm", duration=4),
        ])
        checker = QAChecker()
        summary = checker.check(script)
        kw_results = [r for r in summary.results if r.name == "keywords"]
        assert any(r.status == "warn" for r in kw_results)

    def test_youtube_preset(self):
        script = self._make_script()
        checker = QAChecker({"qa": {"preset": "youtube", "presets": {
            "youtube": {
                "segment_min": 3, "segment_max": 15,
                "duration_per_seg_min": 3, "duration_per_seg_max": 15,
                "total_duration_max": 1200,
                "text_min_len": 15, "text_max_len": 200,
                "min_keywords": 2, "duration_tolerance": 10,
            },
        }}})
        summary = checker.check(script)
        assert checker.preset == "youtube"
        assert checker.segment_min == 3
        assert checker.duration_per_seg_max == 15

    def test_summary_text(self):
        summary = QASummary(total=5, passed=3, warnings=1, failures=1)
        text = QAChecker.summary_text(summary)
        assert "通过 3/5" in text
        assert "警告 1" in text
        assert "失败 1" in text

    def test_check_result_dataclass(self):
        r = CheckResult(name="test", status="pass", message="ok", segment_id=1)
        assert r.name == "test"
        assert r.segment_id == 1
