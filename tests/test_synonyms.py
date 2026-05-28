from core.synonyms import SynonymEngine, _levenshtein


class TestLevenshtein:

    def test_same(self):
        assert _levenshtein("hello", "hello") == 0

    def test_one_insert(self):
        assert _levenshtein("helo", "hello") == 1

    def test_one_delete(self):
        assert _levenshtein("hello", "helo") == 1

    def test_one_replace(self):
        assert _levenshtein("hello", "hallo") == 1

    def test_empty(self):
        assert _levenshtein("", "hello") == 5
        assert _levenshtein("hello", "") == 5

    def test_chinese_characters(self):
        assert _levenshtein("减肥", "减脂") == 1


class TestSynonymEngineScore:

    def test_exact_match(self):
        eng = SynonymEngine()
        assert eng.score("hello", "hello") == 1.0

    def test_synonym_match(self):
        eng = SynonymEngine()
        eng.load_dict({"减肥": ["减脂", "瘦身"]})
        assert eng.score("减肥", "减脂") == 0.8
        assert eng.score("减脂", "减肥") == 0.8

    def test_fuzzy_cn_short(self):
        eng = SynonymEngine()
        s = eng.score("减肥", "减重")
        assert s >= 0.4

    def test_fuzzy_en_short(self):
        eng = SynonymEngine()
        s = eng.score("nature", "natural")
        assert s >= 0.4

    def test_no_match(self):
        eng = SynonymEngine()
        assert eng.score("abc", "xyz") == 0.0
        assert eng.score("减肥", "游泳") == 0.0


class TestSynonymEngineExpand:

    def test_expand_includes_self(self):
        eng = SynonymEngine()
        eng.load_dict({"减肥": ["减脂", "瘦身"]})
        result = eng.expand("减肥")
        assert "减肥" in result
        assert "减脂" in result
        assert "瘦身" in result

    def test_expand_unknown(self):
        eng = SynonymEngine()
        result = eng.expand("unknownxyz")
        assert result == ["unknownxyz"]

    def test_expand_keywords(self):
        eng = SynonymEngine()
        eng.load_dict({"减肥": ["减脂"], "健身": ["运动"]})
        result = eng.expand_keywords(["减肥", "健身"])
        assert "减肥" in result
        assert "减脂" in result
        assert "健身" in result
        assert "运动" in result


class TestSynonymEngineYaml:

    def test_load_default_yaml(self):
        eng = SynonymEngine("data/synonyms.yaml")
        s = eng.score("减肥", "减脂")
        assert s >= 0.8
        s2 = eng.score("减脂", "减肥")
        assert s2 >= 0.8
        s3 = eng.score("减肥", "鱼")
        assert s3 == 0.0


class TestMatcherSynonymIntegration:

    def test_synonym_via_engine(self):
        from core.matcher import Matcher

        class StubDB:
            def search_assets(self, keyword="", type_filter="", limit=100):
                return [type("Asset", (), {"tags": ["减脂"], "file": "test.mp4"})()]

        m = Matcher(StubDB())
        m.load_synonyms({"减肥": ["减脂"]})
        s = m._keyword_score(
            type("Asset", (), {"tags": ["减脂"]})(),
            ["减肥"],
        )
        assert s > 0.0

    def test_fuzzy_via_engine(self):
        from core.matcher import Matcher

        class StubDB:
            def search_assets(self, keyword="", type_filter="", limit=100):
                return [type("Asset", (), {"tags": ["减重"], "file": "test.mp4"})()]

        m = Matcher(StubDB())
        s = m._keyword_score(
            type("Asset", (), {"tags": ["减重"]})(),
            ["减肥"],
        )
        assert s > 0.0
