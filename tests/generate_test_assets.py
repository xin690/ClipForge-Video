"""ClipForge 测试素材生成工具
用 FFmpeg 生成测试用的视频和音频素材。
用法: python tests/generate_test_assets.py
"""

import os
import sys
import subprocess


def run(cmd: list[str]) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, errors='replace', timeout=60)
        if result.returncode != 0:
            print(f"  [WARN] {result.stderr[:100]}")
            return False
        return True
    except FileNotFoundError:
        print("  [ERROR] ffmpeg not found")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    # Ensure FFmpeg is findable
    _ffmpeg_search_dirs = [
        r"C:\Program Files\DownloadHelper CoApp",
        r"C:\ffmpeg\bin",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
    ]
    for d in _ffmpeg_search_dirs:
        if os.path.isdir(d) and d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
    except (FileNotFoundError, OSError):
        print("=" * 50)
        print("ERROR: FFmpeg not found!")
        print("=" * 50)
        print("FFmpeg is required to generate test assets.")
        print()
        print("Install FFmpeg:")
        print("  1. Download from: https://ffmpeg.org/download.html")
        print("  2. Or install via winget: winget install ffmpeg")
        print("  3. Or copy ffmpeg.exe to this directory")
        print()
        print("You can also manually place .mp4 and .mp3 files into:")
        print("  assets/videos/")
        print("  assets/bgm/")
        print()
        sys.exit(1)

    assets_dir = "assets"
    videos_dir = os.path.join(assets_dir, "videos")
    bgm_dir = os.path.join(assets_dir, "bgm")

    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(bgm_dir, exist_ok=True)

    w, h, fps = 1920, 1080, 30

    # Video assets with different colors
    videos = [
        ("knowledge_01", "blue", "knowledge"),
        ("knowledge_02", "lightblue", "knowledge"),
        ("knowledge_03", "darkblue", "knowledge"),
        ("fitness_01", "green", "fitness,motion"),
        ("fitness_02", "darkgreen", "fitness,motion"),
        ("food_01", "orange", "food,healthy"),
        ("food_02", "yellow", "food,healthy"),
        ("tech_01", "purple", "tech,technology"),
        ("business_01", "red", "business,commerce"),
    ]

    print("=" * 50)
    print("ClipForge Test Asset Generator")
    print("=" * 50)

    print(f"\n[1/3] Generating {len(videos)} test videos...")
    for name, color, tags in videos:
        output = os.path.join(videos_dir, f"{name}.mp4")
        if os.path.exists(output):
            print(f"  SKIP {name}.mp4 (exists)")
            continue
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d=10:r={fps}",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-shortest",
            output,
            "-loglevel", "error",
        ]
        if run(cmd):
            print(f"  OK  {name}.mp4 [{color}]")
        else:
            print(f"  FAIL {name}.mp4")

    print(f"\n[2/3] Generating 4 test BGM tracks...")
    bgms = [
        ("bgm_knowledge", 440, "knowledge"),
        ("bgm_news", 523, "news"),
        ("bgm_upbeat", 659, "upbeat"),
        ("bgm_commerce", 392, "commerce"),
    ]
    for name, freq, tags in bgms:
        output = os.path.join(bgm_dir, f"{name}.mp3")
        if os.path.exists(output):
            print(f"  SKIP {name}.mp3 (exists)")
            continue
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"sine=frequency={freq}:duration=30",
            "-acodec", "libmp3lame",
            "-b:a", "128k",
            output,
            "-loglevel", "error",
        ]
        if run(cmd):
            print(f"  OK  {name}.mp3 [{freq}Hz]")
        else:
            print(f"  FAIL {name}.mp3")

    print(f"\n[3/3] Verification...")
    video_count = len([f for f in os.listdir(videos_dir) if f.endswith(".mp4")])
    bgm_count = len([f for f in os.listdir(bgm_dir) if f.endswith(".mp3")])

    print(f"\n{'=' * 50}")
    print(f"Done!")
    print(f"  Videos: {video_count}")
    print(f"  BGM:    {bgm_count}")
    print(f"  Path:   {assets_dir}/")
    print(f"\nNext: Run ClipForge and click 'Scan Assets' in the Asset Browser tab.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
