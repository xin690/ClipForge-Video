import pytest
import os
from core.database import Database
from core.models import Asset


class TestDatabase:
    @pytest.fixture
    def db(self, temp_dir):
        db_path = os.path.join(temp_dir, "test.db")
        db = Database(db_path)
        db.init_tables()
        yield db
        db.close()

    def test_init_tables(self, db):
        conn = db.connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "assets" in table_names
        assert "scripts_history" in table_names

    def test_add_asset(self, db):
        asset = Asset(file="test.mp4", type="video", tags=["测试"])
        asset_id = db.add_asset(asset)
        assert asset_id > 0

    def test_get_asset(self, db):
        asset = Asset(file="test.mp4", type="video", tags=["测试"])
        asset_id = db.add_asset(asset)
        retrieved = db.get_asset(asset_id)
        assert retrieved is not None
        assert retrieved.file == "test.mp4"
        assert "测试" in retrieved.tags

    def test_get_asset_by_file(self, db):
        asset = Asset(file="unique.mp4", type="video", tags=["测试"])
        db.add_asset(asset)
        retrieved = db.get_asset_by_file("unique.mp4")
        assert retrieved is not None
        assert retrieved.file == "unique.mp4"

    def test_search_by_keyword(self, db):
        db.add_asset(Asset(file="food.mp4", type="video", tags=["食物", "减脂"]))
        db.add_asset(Asset(file="gym.mp4", type="video", tags=["健身", "运动"]))
        results = db.search_assets(keyword="减脂")
        assert len(results) == 1
        assert results[0].file == "food.mp4"

    def test_search_by_type(self, db):
        db.add_asset(Asset(file="video.mp4", type="video", tags=["测试"]))
        db.add_asset(Asset(file="music.mp3", type="bgm", tags=["音乐"]))
        results = db.search_assets(type_filter="bgm")
        assert len(results) == 1
        assert results[0].type == "bgm"

    def test_get_all_assets(self, db):
        db.add_asset(Asset(file="a.mp4", type="video"))
        db.add_asset(Asset(file="b.mp3", type="bgm"))
        all_assets = db.get_all_assets()
        assert len(all_assets) == 2

    def test_update_tags(self, db):
        asset = Asset(file="tags.mp4", type="video", tags=["旧标签"])
        asset_id = db.add_asset(asset)
        db.update_asset_tags(asset_id, ["新标签", "更新"])
        updated = db.get_asset(asset_id)
        assert updated is not None
        assert "新标签" in updated.tags
        assert "更新" in updated.tags

    def test_delete_asset(self, db):
        asset = Asset(file="delete.mp4", type="video")
        asset_id = db.add_asset(asset)
        db.delete_asset(asset_id)
        assert db.get_asset(asset_id) is None

    def test_file_exists(self, db):
        db.add_asset(Asset(file="exists.mp4", type="video"))
        assert db.file_exists("exists.mp4") is True
        assert db.file_exists("not_exists.mp4") is False

    def test_asset_count(self, db):
        db.add_asset(Asset(file="a.mp4", type="video"))
        db.add_asset(Asset(file="b.mp3", type="bgm"))
        count = db.get_asset_count()
        assert count["total"] == 2
        assert count.get("video", 0) == 1
        assert count.get("bgm", 0) == 1

    def test_add_batch(self, db):
        assets = [
            Asset(file="a.mp4", type="video"),
            Asset(file="b.mp4", type="video"),
            Asset(file="c.mp3", type="bgm"),
        ]
        count = db.add_assets_batch(assets)
        assert count == 3
        assert db.get_asset_count()["total"] == 3

    def test_script_history(self, db):
        db.add_script_history("测试脚本", '{"title": "test"}')
        history = db.get_script_history()
        assert len(history) >= 1
        assert history[0]["title"] == "测试脚本"
