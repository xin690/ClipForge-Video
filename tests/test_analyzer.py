from core.analyzer import ContentAnalyzer, _run_probe


class TestContentAnalyzerVideo:

    def test_no_ffprobe_graceful(self, temp_dir):
        import os
        fake_path = os.path.join(temp_dir, "does_not_exist.mp4")
        tags = ContentAnalyzer.analyze_video(fake_path)
        assert isinstance(tags, list)
        assert tags == []

    def test_is_list(self):
        tags = ContentAnalyzer.analyze_video("nonexistent.mp4")
        assert isinstance(tags, list)


class TestContentAnalyzerImage:

    def test_no_ffprobe_graceful(self, temp_dir):
        import os
        fake_path = os.path.join(temp_dir, "no_img.jpg")
        tags = ContentAnalyzer.analyze_image(fake_path)
        assert isinstance(tags, list)
        assert tags == []

    def test_is_list(self):
        tags = ContentAnalyzer.analyze_image("nonexistent.jpg")
        assert isinstance(tags, list)


class TestContentAnalyzerBGM:

    def test_no_ffprobe_graceful(self, temp_dir):
        import os
        fake_path = os.path.join(temp_dir, "no_bgm.mp3")
        tags = ContentAnalyzer.analyze_bgm(fake_path)
        assert isinstance(tags, list)
        assert tags == []

    def test_is_list(self):
        tags = ContentAnalyzer.analyze_bgm("nonexistent.mp3")
        assert isinstance(tags, list)


class TestProbeHelper:

    def test_nonexistent_file(self):
        result = _run_probe("nonexistent.mp4")
        assert result is None
