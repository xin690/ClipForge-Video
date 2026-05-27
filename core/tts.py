import asyncio
import hashlib
import json
import re
import time
import os
from pathlib import Path
from functools import lru_cache
from typing import Optional


import logging

_log = logging.getLogger("tts")


_DURATION_CACHE_DIR = Path("./cache/tts_duration")


@lru_cache(maxsize=256)
def preview_duration(text: str, voice: str = "zh-CN-XiaoxiaoNeural", speed: float = 1.0) -> float:
    """估算 TTS 配音时长（秒），零文件 IO。
    
    使用 edge-tts 7.2.8 stream_sync() 从流式元数据获取时长。
    TTSChunk.offset/duration 单位 = 100ns ticks (TICKS_PER_SECOND = 10_000_000)。
    
    Returns:
        时长（秒），edge-tts 失败时 fallback 到字符估算。
    """
    _DURATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"{text}|{voice}|{speed}".encode()).hexdigest()
    cache_path = _DURATION_CACHE_DIR / f"{cache_key}.json"

    if cache_path.exists():
        try:
            entry = json.loads(cache_path.read_text(encoding="utf-8"))
            if time.time() - entry["ts"] < 604800:
                return entry["duration"]
        except Exception:
            pass

    duration = 0.0
    try:
        from edge_tts import Communicate
        last_offset = last_duration = 0
        rate_pct = f"{int((speed - 1.0) * 100):+d}%"
        for chunk in Communicate(text, voice, rate=rate_pct, boundary="WordBoundary").stream_sync():
            if chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                last_offset = chunk["offset"]
                last_duration = chunk["duration"]
        if last_duration:
            duration = (last_offset + last_duration) / 10_000_000
    except Exception as e:
        _log.warning("edge-tts 流式获取时长失败: %s", e)

    if duration <= 0:
        cn = len(re.findall(r'[\u4e00-\u9fff]', text))
        en = len(re.findall(r'[a-zA-Z]', text))
        duration = (cn * 0.3 + en * 0.15) / speed

    duration = max(duration, 1.0)

    try:
        cache_path.write_text(json.dumps({"ts": time.time(), "duration": duration}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return duration


class TTSModule:
    def __init__(self, config: dict):
        self.engine = config.get("tts", {}).get("engine", "edge-tts")
        self.voice = config.get("tts", {}).get("voice", "zh-CN-XiaoxiaoNeural")
        self.speed = config.get("tts", {}).get("speed", 1.0)
        cache_dir = config.get("paths", {}).get("cache", "./cache")
        self.cache_dir = Path(cache_dir) / "tts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._semaphore = asyncio.Semaphore(3)

    def generate(self, text: str, output_path: str, voice: Optional[str] = None) -> str:
        effective_voice = voice or self.voice
        _log.debug("generate voice=%s effective=%s text=%s", voice, effective_voice, text[:20])
        cached = self._check_cache(text, effective_voice)
        if cached:
            import shutil
            shutil.copy2(cached, output_path)
            return output_path

        if self.engine == "edge-tts":
            result = self._edge_tts(text, output_path, effective_voice)
        else:
            result = self._fallback_tts(text, output_path)

        if result:
            self._save_cache(text, result, effective_voice)
        return result

    def generate_batch(self, segments: list[tuple[int, str]], output_dir: str, voice: Optional[str] = None) -> list[str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[str] = []

        for seg_id, text in segments:
            out_path = str(output_dir / f"voice_{seg_id:04d}.wav")
            result = self.generate(text, out_path, voice=voice)
            results.append(result)

        return results

    def generate_batch_async(self, segments: list[tuple[int, str]], output_dir: str, voice: Optional[str] = None) -> list[str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        async def _run_all():
            tasks = []
            for seg_id, text in segments:
                out_path = str(output_dir / f"voice_{seg_id:04d}.wav")
                tasks.append(self._async_generate(text, out_path, voice=voice))
            return await asyncio.gather(*tasks)

        try:
            results = asyncio.run(_run_all())
            return [r for r in results if r]
        except RuntimeError:
            results = []
            for seg_id, text in segments:
                out_path = str(output_dir / f"voice_{seg_id:04d}.wav")
                results.append(self.generate(text, out_path, voice=voice))
            return results

    def _edge_tts(self, text: str, output_path: str, voice: Optional[str] = None) -> str:
        async def _do():
            import edge_tts
            rate = f"{int((self.speed - 1) * 50):+d}%"
            communicate = edge_tts.Communicate(text, voice or self.voice, rate=rate)
            await communicate.save(output_path)
            return output_path

        try:
            return asyncio.run(_do())
        except Exception as e:
            _log.warning("edge-tts 失败 (%s), 回退到 pyttsx3", e)
            return self._fallback_tts(text, output_path)

    def _fallback_tts(self, text: str, output_path: str) -> str:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            _log.warning("pyttsx3 失败 (%s), 回退到静音配音", e)
        _log.warning("TTS 全部引擎不可用，将生成静音配音: %s", text[:30])
        return self._silent_audio(text, output_path)

    def _silent_audio(self, text: str, output_path: str) -> str:
        duration = max(len(text) * 0.15, 2.0)
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            "-acodec", "pcm_s16le",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
        except Exception:
            pass
        return output_path if os.path.exists(output_path) else ""

    async def _async_generate(self, text: str, output_path: str, voice: Optional[str] = None) -> Optional[str]:
        effective_voice = voice or self.voice
        cached = self._check_cache(text, effective_voice)
        if cached:
            import shutil
            shutil.copy2(cached, output_path)
            return output_path

        async with self._semaphore:
            try:
                import edge_tts
                rate = f"{int((self.speed - 1) * 50):+d}%"
                communicate = edge_tts.Communicate(text, effective_voice, rate=rate)
                await communicate.save(output_path)
                self._save_cache(text, output_path, effective_voice)
                return output_path
            except Exception:
                return self._fallback_tts(text, output_path)

    def _check_cache(self, text: str, voice: Optional[str] = None) -> Optional[str]:
        key = self._cache_key(text, voice)
        cached_file = self.cache_dir / f"{key}.wav"
        if not cached_file.exists():
            return None
        if self._is_silent(str(cached_file)):
            _log.warning("缓存文件为静音，忽略并删除: %s", cached_file)
            cached_file.unlink(missing_ok=True)
            return None
        return str(cached_file)

    def _save_cache(self, text: str, output_path: str, voice: Optional[str] = None):
        if not os.path.exists(output_path):
            return
        if self._is_silent(output_path):
            return
        key = self._cache_key(text, voice)
        cached_file = self.cache_dir / f"{key}.wav"
        if not cached_file.exists():
            import shutil
            shutil.copy2(output_path, cached_file)

    @staticmethod
    def _cache_key(text: str, voice: Optional[str] = None) -> str:
        raw = f"{voice or ''}:{text}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _is_silent(path: str) -> bool:
        try:
            import subprocess
            r = subprocess.run(
                ["ffmpeg", "-v", "info", "-i", path,
                 "-af", "volumedetect", "-t", "2.0",
                 "-f", "null", "-"],
                capture_output=True, timeout=10,
            )
            err = r.stderr.decode(errors="replace")
            return "mean_volume: -inf" in err
        except Exception:
            return not os.path.exists(path) or os.path.getsize(path) < 5000
