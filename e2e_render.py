"""End-to-end render: scan assets → build timeline → render video + audio + subs."""
import os, sys, json, shutil, subprocess, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("e2e")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

from core.config import load_config, get
from core.database import Database
from core.scanner import AssetScanner
from core.matcher import Matcher
from core.rules import RuleEngine
from core.timeline import TimelineBuilder
from core.tts import TTSModule
from core.renderer import Renderer
from core.models import Script

SCRIPT_PATH = sys.argv[1] if len(sys.argv) > 1 else "scripts/sample_knowledge.json"
OUTPUT_DIR = "output"
OUTPUT_FILENAME = Path(SCRIPT_PATH).stem + ".mp4"
VIDEO_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)


def step_log(step: int, total: int, msg: str):
    sep = "=" * 52
    logger.info(f"\n{sep}\nSTEP {step}/{total}: {msg}\n{sep}")


def ensure_ffmpeg():
    # Prefer full FFmpeg with libass
    for d in [r"C:\ffmpeg\bin", r"C:\Program Files\DownloadHelper CoApp", r"C:\Program Files\ffmpeg\bin"]:
        if os.path.isdir(d):
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
                logger.info(f"Found ffmpeg in: {d}")
                return True
            except FileNotFoundError:
                pass
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return True
    except FileNotFoundError:
        return False


def scan_assets():
    db_path = get("paths.database", "./database/clipforge.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = Database(db_path)
    db.init_tables()
    scanner = AssetScanner(db, get("paths.assets", "./assets"))
    count = scanner.scan_all()
    assets = db.get_all_assets()
    logger.info(f"Scanned {count}, total in DB: {len(assets)}")
    for a in assets:
        logger.info(f"  [{a.type}] {a.file}  tags={a.tags}")
    db.close()


def render(script_path: str):
    config = load_config()
    db = Database(get("paths.database", "./database/clipforge.db"))
    db.init_tables()

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    script = Script(**script_data)
    logger.info(f"Script: {script.title} ({len(script.segments)} segments)")

    # Build timeline
    matcher = Matcher(db)
    rule_engine = RuleEngine()
    rule_engine.register_defaults()
    builder = TimelineBuilder(matcher, rule_engine)

    logger.info("Matching assets...")
    for seg in script.segments:
        assets = matcher.match(seg.text, seg.keywords, top_k=3)
        logger.info(f"  seg {seg.id} [{','.join(seg.keywords)}] → {len(assets)} assets")

    timeline = builder.build(script)
    dur = timeline.timeline[-1].end
    logger.info(f"Timeline: {len(timeline.timeline)} clips, total={dur:.0f}s")
    for item in timeline.timeline:
        logger.info(f"  {item.asset} | {item.transition} | {item.subtitle_style} | {item.start:.0f}s-{item.end:.0f}s"
                    f"  \"{item.subtitle[:30]}...\"")

    # Generate voice files
    voice_dir = Path(OUTPUT_DIR) / "_voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    tts_module = TTSModule(config)
    tts_module.generate_batch([(seg.id, seg.text) for seg in script.segments], str(voice_dir))
    voice_files = sorted(
        [str(voice_dir / f) for f in os.listdir(voice_dir) if f.endswith(".wav")],
        key=lambda x: int(Path(x).stem.replace("voice_", ""))
    )
    for item, vf in zip(timeline.timeline, voice_files):
        item.voice_file = vf
    logger.info(f"Voice: {len(voice_files)} files")

    # Render (handles subs + voice + BGM internally)
    assets_dir = get("paths.assets", "./assets")
    bgm_path = os.path.join(assets_dir, "bgm", script.bgm) if script.bgm else None
    if bgm_path and not os.path.exists(bgm_path):
        bgm_path = None
    if bgm_path:
        logger.info(f"BGM: {os.path.basename(bgm_path)}")

    renderer = Renderer(config)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info("Rendering...")
    result = renderer.render(
        timeline=timeline,
        output_path=VIDEO_PATH,
        assets_dir=assets_dir,
        bgm_file=bgm_path,
        progress_callback=lambda p: logger.info(f"  render: {p*100:.0f}%"),
    )

    db.close()
    return result


def verify(video_path: str):
    """Print video stream info."""
    if not os.path.exists(video_path):
        logger.error(f"File not found: {video_path}")
        return
    r = subprocess.run(["ffmpeg", "-i", video_path], capture_output=True, text=True, errors='replace', timeout=15)
    for line in r.stderr.split("\n"):
        if any(k in line for k in ["Stream", "Duration", "bitrate"]):
            logger.info(f"  {line.strip()}")


def main():
    if not ensure_ffmpeg():
        logger.error("FFmpeg not found!")
        sys.exit(1)

    step_log(1, 3, "Scanning assets")
    scan_assets()

    step_log(2, 3, "Rendering video (subs + voice + BGM)")
    result = render(SCRIPT_PATH)

    step_log(3, 3, "Verification")
    verify(result)
    logger.info(f"  Path: {os.path.abspath(result)}")
    logger.info(f"  Size: {os.path.getsize(result) / 1024 / 1024:.1f} MB")

    # Cleanup
    for d in [Path(OUTPUT_DIR) / "_voice"]:
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
