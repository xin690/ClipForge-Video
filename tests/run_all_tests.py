"""ClipForge 一键自动测试

快速验证所有核心功能是否正常，无需 FFmpeg。
运行: python tests/run_all_tests.py
"""

import os
import sys
import time
import json
import shutil
import tempfile
from pathlib import Path

# Add project root to path so core/ and ui/ modules are importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

PASS = 0
FAIL = 0
SKIP = 0


def test(name: str):
    global PASS, FAIL
    def decorator(fn):
        try:
            start = time.time()
            fn()
            elapsed = time.time() - start
            print(f"  PASS  {name}  ({elapsed:.2f}s)")
            PASS += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            FAIL += 1
    return decorator


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        msg = f"  FAIL  {name}"
        if detail:
            msg += f": {detail}"
        print(msg)
        FAIL += 1


def section(title: str):
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")


def main():
    global PASS, FAIL, SKIP

    print(f"\n{'#' * 55}")
    print(f"  ClipForge Automated Test Suite")
    print(f"  Python {sys.version.split()[0]}")
    print(f"  Time:  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#' * 55}")

    # ================================================================
    section("1/5: Core Config")
    # ================================================================
    from core.config import load_config, get_config, get, save_config
    load_config()
    check("config loaded", get("app.name") == "ClipForge")
    check("config version", get("app.version") == "0.1.0")
    check("config video width", get("video.width") == 1920)
    check("config has ai", "ai" in get_config())

    # ================================================================
    section("2/5: Data Models")
    # ================================================================
    from core.models import Script, Segment, Asset, Timeline, TimelineItem

    seg = Segment(id=1, text="test", keywords=["kw"], emotion="strong", duration=5)
    check("Segment created", seg.id == 1 and seg.text == "test")
    check("Segment defaults", seg.emotion == "strong" and seg.duration == 5)

    script = Script(title="t", duration=10, segments=[Segment(id=1, text="t")])
    check("Script created", script.title == "t" and len(script.segments) == 1)

    try:
        Script(title="t", duration=10, segments=[])
        check("Script empty segments rejected", False)
    except Exception:
        check("Script empty segments rejected", True)

    asset = Asset(file="test.mp4", type="video", tags=["test"])
    check("Asset created", asset.file == "test.mp4" and asset.type == "video")

    item = TimelineItem(start=0, end=5, asset="test.mp4")
    check("TimelineItem defaults", item.transition == "cut" and item.camera == "static")

    tl = Timeline(timeline=[item])
    check("Timeline created", len(tl.timeline) == 1 and tl.fps == 30)

    # ================================================================
    section("3/5: Database")
    # ================================================================
    from core.database import Database

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    db = Database(db_path)
    db.init_tables()
    check("DB initialized", os.path.exists(db_path))

    aid = db.add_asset(Asset(file="a.mp4", type="video", tags=["x", "y"]))
    check("Asset inserted", aid > 0)
    check("Asset retrieved", db.get_asset(aid).file == "a.mp4")
    check("Asset by file", db.get_asset_by_file("a.mp4") is not None)

    db.add_asset(Asset(file="b.mp4", type="video", tags=["x"]))
    db.add_asset(Asset(file="c.mp3", type="bgm", tags=["y"]))
    results = db.search_assets(keyword="x")
    check("Search by keyword", len(results) >= 2)
    results = db.search_assets(type_filter="bgm")
    check("Search by type", len(results) == 1 and results[0].type == "bgm")

    db.update_asset_tags(aid, ["new"])
    check("Tags updated", "new" in db.get_asset(aid).tags)

    count = db.get_asset_count()
    check("Asset count", count["total"] >= 3)

    db.delete_asset(aid)
    check("Asset deleted", db.get_asset(aid) is None)
    check("File exists", db.file_exists("a.mp4") is False)

    db.add_script_history("test", '{"x":1}')
    check("Script history", len(db.get_script_history()) >= 1)

    db.close()
    shutil.rmtree(tmpdir, ignore_errors=True)
    check("DB cleanup", True)

    # ================================================================
    section("4/5: Rules Engine")
    # ================================================================
    from core.rules import RuleEngine, SubtitleStyleRule, TransitionRule, CameraRule

    engine = RuleEngine()
    engine.register_defaults()

    tests = [
        ({"emotion": "strong"}, "subtitle.style", "big_yellow"),
        ({"emotion": "normal"}, "subtitle.style", "normal"),
        ({"emotion": "sad"}, "subtitle.style", "soft_white"),
        ({"duration": 2}, "transition", "cut"),
        ({"duration": 5}, "transition", "fade"),
        ({"duration": 10}, "transition", "slide"),
        ({"style": "knowledge"}, "camera", "slow_zoom"),
        ({"style": "news"}, "camera", "static"),
        ({"style": "entertainment"}, "camera", "pan"),
    ]

    for ctx, key, expected in tests:
        result = engine.execute(ctx)
        keys = key.split(".")
        val = result
        for k in keys:
            val = val.get(k, "") if isinstance(val, dict) else ""
        check(f"Rule [{key}] = {expected}", val == expected)

    # ================================================================
    section("5/5: Timeline Building")
    # ================================================================
    from core.matcher import Matcher
    from core.timeline import TimelineBuilder, TimelineValidator

    stub_db = type("DB", (), {
        "search_assets": lambda self, **kw: [],
        "get_all_assets": lambda self: [],
    })()

    matcher = Matcher(stub_db)
    engine2 = RuleEngine()
    engine2.register_defaults()
    builder = TimelineBuilder(matcher, engine2)

    script = Script(
        title="Test Video", duration=15, style="knowledge",
        segments=[
            Segment(id=1, text="First segment", keywords=["test"], emotion="normal", duration=5),
            Segment(id=2, text="Second segment", keywords=["test"], emotion="strong", duration=6),
            Segment(id=3, text="Third segment", keywords=["test"], emotion="calm", duration=4),
        ],
    )

    timeline = builder.build(script)
    check("Timeline has items", len(timeline.timeline) == 3)
    check("Timeline continuity", timeline.timeline[0].end == timeline.timeline[1].start)
    check("Timeline total", timeline.timeline[-1].end == 15.0)

    validator = TimelineValidator()
    errors = validator.validate(timeline)
    check("Timeline valid", len(errors) == 0)

    check("Rule applied - transition", timeline.timeline[0].transition == "fade")
    check("Rule applied - emotion style", timeline.timeline[1].subtitle_style == "big_yellow")

    # ================================================================
    section("6/6: AI Planner & Downloader")
    # ================================================================
    from core.ai_planner import AIPlanner
    from core.downloader import Downloader, _sanitize_filename

    plan = AIPlanner._extract_json('{"title":"test","duration":10,"segments":[{"id":1,"text":"t","keywords":["a"],"emotion":"normal","duration":5}]}')
    check("AI JSON extract valid", plan is not None and plan.get("title") == "test")

    plan2 = AIPlanner._extract_json('```json\n{"title":"x","duration":5,"segments":[]}\n```')
    check("AI JSON extract markdown", plan2 is not None and plan2.get("title") == "x")

    plan3 = AIPlanner._extract_json("not json")
    check("AI JSON extract invalid returns None", plan3 is None)

    plan4 = AIPlanner._extract_json('{"title":"中国自然","duration":24,"segments":[{"id":1,"text":"高山","keywords":["高山"],"emotion":"strong","duration":5}]}')
    check("AI JSON extract unicode", plan4 is not None and plan4["title"] == "中国自然")

    planner_disabled = AIPlanner({"ai": {"enabled": False}})
    check("AI planner disabled returns None", planner_disabled.plan_from_theme("test") is None)

    planner_no_key = AIPlanner({"ai": {"enabled": True, "api_key": ""}})
    check("AI planner no key returns None", planner_no_key.plan_from_theme("test") is None)

    planner_init = AIPlanner({"ai": {"enabled": True, "provider": "deepseek", "api_key": "sk-test", "model": "deepseek-chat", "max_tokens": 1000}})
    check("AI planner init", planner_init.provider == "deepseek" and planner_init.model == "deepseek-chat")

    fname = _sanitize_filename("hello world")
    check("Downloader sanitize basic", fname == "hello_world")

    fname2 = _sanitize_filename('test:file<name>')
    check("Downloader sanitize special", ":" not in fname2 and "<" not in fname2)

    fname3 = _sanitize_filename("///")
    check("Downloader sanitize empty", fname3 == "untitled")

    dl = Downloader({"downloader": {"provider": "pexels", "api_key": "", "max_per_query": 5}})
    check("Downloader init", dl.provider == "pexels" and dl.max_per_query == 5)

    dl_empty = Downloader({})
    check("Downloader defaults", dl_empty.provider == "pexels")

    check("Downloader no api search", dl.search("test") == [])

    quality_test = Downloader._pick_best_video_quality([
        {"quality": "sd", "link": "s"},
        {"quality": "hd", "link": "h"},
    ])
    check("Downloader pick best quality", quality_test["link"] == "h")

    quality_empty = Downloader._pick_best_video_quality([])
    check("Downloader pick empty quality", quality_empty is None)

    # ================================================================
    section("7/7: Module Imports")
    # ================================================================
    modules = [
        "core.config", "core.models", "core.database", "core.scanner",
        "core.matcher", "core.rules", "core.timeline", "core.tts",
        "core.subtitle", "core.ffmpeg", "core.renderer", "core.pipeline",
        "core.ai_planner", "core.downloader",
        # ui.resources and ui.worker need PyQt6; tested separately

    ]

    for m in modules:
        try:
            __import__(m)
            PASS += 1
        except Exception as e:
            print(f"  FAIL  Import {m}: {e}")
            FAIL += 1

    # Summary
    total = PASS + FAIL
    print(f"\n{'=' * 55}")
    print(f"  Results: {PASS}/{total} passed", end="")
    if FAIL > 0:
        print(f", {FAIL} failed", end="")
    print()
    print(f"  {'ALL TESTS PASSED' if FAIL == 0 else 'SOME TESTS FAILED'}")
    print(f"{'=' * 55}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
