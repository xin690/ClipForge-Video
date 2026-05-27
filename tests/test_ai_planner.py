import pytest
import json
from core.ai_planner import AIPlanner


class TestAIPlannerExtractJSON:
    def test_extract_valid_json(self):
        result = AIPlanner._extract_json('{"title":"test","duration":10,"segments":[]}')
        assert result == {"title": "test", "duration": 10, "segments": []}

    def test_extract_json_with_markdown_block(self):
        result = AIPlanner._extract_json('```json\n{"title":"test","duration":10,"segments":[]}\n```')
        assert result == {"title": "test", "duration": 10, "segments": []}

    def test_extract_json_with_surrounding_text(self):
        result = AIPlanner._extract_json('这是AI的分析结果\n{"title":"test","duration":10,"segments":[]}\n分析完成')
        assert result == {"title": "test", "duration": 10, "segments": []}

    def test_extract_nested_json(self):
        result = AIPlanner._extract_json('{"title":"test","duration":20,"segments":[{"id":1,"text":"text","keywords":["a","b"],"emotion":"normal","duration":5}]}')
        assert result["segments"][0]["text"] == "text"
        assert result["segments"][0]["keywords"] == ["a", "b"]

    def test_extract_unicode_json(self):
        result = AIPlanner._extract_json('{"title":"中国自然风光","duration":24,"segments":[{"id":1,"text":"巍峨的高山","keywords":["高山"],"emotion":"strong","duration":5}]}')
        assert result["title"] == "中国自然风光"

    def test_extract_invalid_json_returns_none(self):
        result = AIPlanner._extract_json('not a json object')
        assert result is None

    def test_extract_empty_string_returns_none(self):
        result = AIPlanner._extract_json('')
        assert result is None

    def test_extract_array_returns_inner_object(self):
        result = AIPlanner._extract_json('[{"id":1}]')
        assert isinstance(result, dict) and result.get("id") == 1


class TestAIPlannerDisabled:
    def test_plan_from_theme_disabled(self):
        planner = AIPlanner({"ai": {"enabled": False, "api_key": ""}})
        result = planner.plan_from_theme("测试主题")
        assert result is None

    def test_plan_from_theme_no_api_key(self):
        planner = AIPlanner({"ai": {"enabled": True, "api_key": ""}})
        result = planner.plan_from_theme("测试主题")
        assert result is None

    def test_suggest_search_queries_disabled(self):
        planner = AIPlanner({"ai": {"enabled": False, "api_key": ""}})
        from core.models import Segment
        segs = [Segment(id=1, text="test", keywords=["a"], duration=5)]
        result = planner.suggest_search_queries(segs)
        assert len(result) == 0

    def test_suggest_search_queries_empty(self):
        planner = AIPlanner({"ai": {"enabled": True, "api_key": "test"}})
        result = planner.suggest_search_queries([])
        assert result == []


class TestAIPlannerInit:
    def test_default_config(self):
        planner = AIPlanner({
            "ai": {"enabled": True, "provider": "deepseek", "api_key": "sk-test", "model": "deepseek-chat"}
        })
        assert planner.enabled is True
        assert planner.provider == "deepseek"
        assert planner.api_key == "sk-test"
        assert planner.model == "deepseek-chat"

    def test_missing_config_uses_defaults(self):
        planner = AIPlanner({})
        assert planner.enabled is False
        assert planner.provider == "openai"
        assert planner.api_key == ""

    def test_api_url_mapping(self):
        planner = AIPlanner({"ai": {"enabled": True, "provider": "qwen"}})
        url = planner._api_url()
        assert "aliyuncs.com" in url

        planner2 = AIPlanner({"ai": {"enabled": True, "provider": "deepseek"}})
        url2 = planner2._api_url()
        assert "deepseek.com" in url2
