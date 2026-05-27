import pytest
import json
import os
from core.database import Database
from core.scanner import AssetScanner
from core.matcher import Matcher
from core.rules import RuleEngine
from core.timeline import TimelineBuilder
from core.models import Script, Segment


class TestIntegration:
    @pytest.fixture
    def db(self, temp_dir):
        db_path = os.path.join(temp_dir, "test_integration.db")
        db = Database(db_path)
        db.init_tables()

        db.add_asset_batch = type(db)._old_batch if hasattr(db, "_old_batch") else db.add_assets_batch

        from core.models import Asset
        db.add_assets_batch([
            Asset(file="food01.mp4", type="video", duration=8.0, tags=["减脂", "沙拉", "低卡"], width=1920, height=1080),
            Asset(file="gym01.mp4", type="video", duration=10.0, tags=["健身", "运动", "跑步"], width=1920, height=1080),
            Asset(file="bgm_knowledge.mp3", type="bgm", duration=30.0, tags=["轻快", "知识", "背景"], width=0, height=0),
        ])

        yield db
        db.close()

    def test_scan_to_match_flow(self, db, temp_dir):
        assets_dir = os.path.join(temp_dir, "assets")
        videos_dir = os.path.join(assets_dir, "videos")
        os.makedirs(videos_dir, exist_ok=True)

        test_file = os.path.join(videos_dir, "test_food.mp4")
        with open(test_file, "w") as f:
            f.write("fake video content")

        scanner = AssetScanner(db, assets_dir)
        count = scanner.scan_all()
        assert count > 0

    def test_script_to_timeline_flow(self, db):
        matcher = Matcher(db)
        rules = RuleEngine()
        rules.register_defaults()
        builder = TimelineBuilder(matcher, rules)

        script = Script(
            title="整合测试",
            duration=15,
            style="knowledge",
            segments=[
                {"id": 1, "text": "减脂很重要", "keywords": ["减脂"], "emotion": "normal", "duration": 5},
                {"id": 2, "text": "运动也很重要", "keywords": ["健身"], "emotion": "strong", "duration": 5},
            ],
        )

        timeline = builder.build(script)
        assert len(timeline.timeline) == 2
        assert timeline.timeline[0].asset != ""
        assert timeline.timeline[1].asset != ""

    def test_full_pipeline_mock(self, db, temp_dir):
        matcher = Matcher(db)
        rules = RuleEngine()
        rules.register_defaults()
        builder = TimelineBuilder(matcher, rules)

        script = Script(
            title="管线测试",
            duration=10,
            segments=[Segment(id=1, text="减脂知识", keywords=["减脂"], duration=5)],
        )
        timeline = builder.build(script)
        assert len(timeline.timeline) == 1
        assert timeline.timeline[0].subtitle == "减脂知识"
