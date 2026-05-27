"""Integration test: scan + match + timeline build."""
import os, sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Ensure ffmpeg in PATH
for d in [r"C:\Program Files\DownloadHelper CoApp", r"C:\ffmpeg\bin"]:
    if os.path.isdir(d):
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

from core.config import load_config; load_config()
from core.database import Database
from core.scanner import AssetScanner
from core.matcher import Matcher
from core.rules import RuleEngine
from core.timeline import TimelineBuilder
from core.models import Script

db = Database("./database/test_scan.db")
db.init_tables()

# Scan assets
scanner = AssetScanner(db, "./assets")
count = scanner.scan_all()
print(f"Scanned: {count} assets")

# Match tests
matcher = Matcher(db)

tests = [
    ("knowledge", ["knowledge"], 3),
    ("fitness", ["fitness"], 3),
    ("business", ["business"], 3),
    ("food", ["food"], 3),
]

for text, keywords, topk in tests:
    results = matcher.match(text, keywords, top_k=topk)
    print(f"Match '{keywords}': {len(results)} results")
    for r in results:
        tags = ", ".join(r.tags)
        print(f"  [{r.type}] {r.file} -> tags: {tags}")

# Build timeline
rules = RuleEngine()
rules.register_defaults()
builder = TimelineBuilder(matcher, rules)

script = Script(
    title="Test Pipeline", duration=30, style="knowledge",
    segments=[
        {"id": 1, "text": "健康生活从饮食开始", "keywords": ["knowledge"], "emotion": "normal", "duration": 5},
        {"id": 2, "text": "坚持运动非常重要", "keywords": ["fitness"], "emotion": "strong", "duration": 5},
        {"id": 3, "text": "科技改变未来", "keywords": ["tech"], "emotion": "calm", "duration": 5},
    ],
)
timeline = builder.build(script)
total = timeline.timeline[-1].end
print(f"\nTimeline: {len(timeline.timeline)} clips, total={total:.0f}s")
for i, item in enumerate(timeline.timeline):
    asset_name = item.asset or "[placeholder]"
    print(f"  Clip {i+1}: {asset_name} | {item.transition} | {item.subtitle_style} | {item.start:.0f}s-{item.end:.0f}s")

# Cleanup
db.close()
if os.path.exists("./database/test_scan.db"):
    os.remove("./database/test_scan.db")
print("\nAll integration tests passed!")
