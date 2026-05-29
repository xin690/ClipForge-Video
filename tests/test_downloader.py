import pytest
import os
import tempfile
from core.downloader import Downloader, _sanitize_filename


class TestSanitizeFilename:
    def test_basic(self):
        assert _sanitize_filename("hello world") == "hello_world"

    def test_special_chars(self):
        result = _sanitize_filename('test:file<name>')
        assert ":" not in result and "<" not in result

    def test_spaces(self):
        assert _sanitize_filename("mountain landscape drone") == "mountain_landscape_drone"

    def test_max_length(self):
        result = _sanitize_filename("a" * 200, max_len=50)
        assert len(result) <= 50

    def test_unicode(self):
        result = _sanitize_filename("mountain_landscape_中国")
        assert result == "mountain_landscape_中国"

    def test_trailing_underscore_removed(self):
        result = _sanitize_filename("test//name")
        assert not result.endswith("_")

    def test_empty_returns_untitled(self):
        result = _sanitize_filename("///")
        assert result == "untitled"


class TestDownloaderInit:
    def test_defaults(self):
        dl = Downloader({})
        assert dl.pexels_key == ""
        assert dl.pixabay_key == ""
        assert dl.max_per_query == 3

    def test_custom_config(self):
        dl = Downloader({
            "downloader": {
                "pexels_key": "pex-key",
                "pixabay_key": "pix-key",
                "max_per_query": 5,
                "min_width": 1280,
                "timeout": 60,
            }
        })
        assert dl.pexels_key == "pex-key"
        assert dl.pixabay_key == "pix-key"
        assert dl.max_per_query == 5
        assert dl.min_width == 1280

    def test_legacy_config_fallback(self):
        dl = Downloader({
            "downloader": {
                "provider": "pexels",
                "api_key": "legacy-key",
            }
        })
        assert dl.pexels_key == "legacy-key"
        assert dl.pixabay_key == ""

        dl2 = Downloader({
            "downloader": {
                "provider": "pixabay",
                "api_key": "old-key",
            }
        })
        assert dl2.pexels_key == ""
        assert dl2.pixabay_key == "old-key"


class TestDownloaderNoApi:
    def test_search_no_api_key(self):
        dl = Downloader({"downloader": {}})
        results = dl.search("test")
        assert results == []

    def test_search_and_download_no_api_key(self):
        dl = Downloader({"downloader": {}})
        results = dl.search_and_download([{"segment_id": 1, "query": "test"}], "./test_assets")
        assert results == []

    def test_check_configured_false(self):
        dl = Downloader({})
        assert dl._check_configured() is False

    def test_check_configured_true(self):
        dl = Downloader({"downloader": {"pexels_key": "test"}})
        assert dl._check_configured() is True


class TestVideoQualityPicker:
    def test_pick_best_quality_4k_preferred(self):
        files = [
            {"quality": "sd", "link": "sd_url"},
            {"quality": "hd", "link": "hd_url"},
            {"quality": "4k", "link": "4k_url"},
        ]
        best = Downloader._pick_best_video_quality(files)
        assert best["link"] == "4k_url"

    def test_pick_best_quality_hd_fallback(self):
        files = [
            {"quality": "sd", "link": "sd_url"},
            {"quality": "hd", "link": "hd_url"},
        ]
        best = Downloader._pick_best_video_quality(files)
        assert best["link"] == "hd_url"

    def test_pick_best_quality_empty(self):
        assert Downloader._pick_best_video_quality([]) is None

    def test_pick_pixabay_quality(self):
        videos = {
            "large": {"url": "large_url"},
            "medium": {"url": "medium_url"},
            "small": {"url": "small_url"},
        }
        best = Downloader._pick_best_video_quality_pixabay(videos)
        assert best == "large_url"

    def test_pick_pixabay_fallback(self):
        videos = {
            "small": {"url": "small_url"},
        }
        best = Downloader._pick_best_video_quality_pixabay(videos)
        assert best == "small_url"

    def test_pick_pixabay_empty(self):
        assert Downloader._pick_best_video_quality_pixabay({}) is None
