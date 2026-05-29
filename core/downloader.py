import os
import re
import logging
from pathlib import Path
from typing import Optional, Callable

import httpx

from core.database import Database
from core.scanner import AssetScanner

_log = logging.getLogger("downloader")

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"
PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
PIXABAY_PHOTO_URL = "https://pixabay.com/api/"

STYLE_KEYWORDS = {
    "knowledge": ["documentary", "educational", "explainer", "science"],
    "news": ["breaking", "report", "interview", "footage"],
    "entertainment": ["fun", "vlog", "lifestyle", "trending"],
    "commerce": ["product", "commercial", "promo", "advertisement"],
}

EMOTION_KEYWORDS = {
    "normal": ["neutral", "daily", "casual"],
    "strong": ["dynamic", "bold", "energetic"],
    "happy": ["joyful", "fun", "bright"],
    "sad": ["calm", "gentle", "moody"],
    "calm": ["peaceful", "soft", "serene"],
}


def _sanitize_filename(text: str, max_len: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|]', '_', text)
    name = re.sub(r'\s+', '_', name).strip('_')
    if len(name) > max_len:
        name = name[:max_len].rstrip('_')
    return name or "untitled"


def expand_search_queries(keywords: list[str], style: str = "",
                           emotion: str = "") -> list[str]:
    queries = set()
    base = " ".join(keywords).strip()
    if base:
        queries.add(base)
    style_kw = STYLE_KEYWORDS.get(style, [])
    if style_kw and base:
        queries.add(f"{base} {style_kw[0]}")
    emotion_kw = EMOTION_KEYWORDS.get(emotion, [])
    if emotion_kw and base:
        queries.add(f"{base} {emotion_kw[0]}")
    return list(queries)[:3]


class Downloader:
    def __init__(self, config: dict):
        dl_cfg = config.get("downloader", {})
        self.pexels_key = dl_cfg.get("pexels_key", "") or (
            dl_cfg.get("api_key", "") if dl_cfg.get("provider", "") == "pexels" else ""
        )
        self.pixabay_key = dl_cfg.get("pixabay_key", "") or (
            dl_cfg.get("api_key", "") if dl_cfg.get("provider", "") == "pixabay" else ""
        )
        self.max_per_query = dl_cfg.get("max_per_query", 3)
        self.min_width = dl_cfg.get("min_width", 1920)
        self.timeout = dl_cfg.get("timeout", 120)

    def _check_configured(self) -> bool:
        if not self.pexels_key and not self.pixabay_key:
            _log.warning("下载器 API Key 未配置（至少需要 Pexels 或 Pixabay 一个 Key）")
            return False
        return True

    def search(self, query: str, media_type: str = "video", per_page: int | None = None) -> list[dict]:
        if not self._check_configured():
            return []
        per_page = per_page or self.max_per_query
        all_results = []
        if self.pexels_key:
            all_results.extend(self._search_pexels(query, media_type, per_page))
        if self.pixabay_key:
            all_results.extend(self._search_pixabay(query, media_type, per_page))
        seen = set()
        unique = []
        for r in all_results:
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u)
                unique.append(r)
        unique.sort(key=lambda r: (-r.get("width", 0) * r.get("height", 0)))
        return [r for r in unique if r.get("width", 0) >= self.min_width]

    def _search_pexels(self, query: str, media_type: str, per_page: int) -> list[dict]:
        headers = {"Authorization": self.pexels_key}
        params = {"query": query, "per_page": per_page}

        if media_type == "photo":
            url = PEXELS_PHOTO_URL
            params["orientation"] = "landscape"
            params["size"] = "large"
        else:
            url = PEXELS_VIDEO_URL
            params["orientation"] = "landscape"
            params["size"] = "large"

        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code != 200:
                _log.warning("Pexels API 返回 %d: %s", resp.status_code, resp.text[:200])
                return []
            data = resp.json()

            results = []
            items = data.get("videos", []) if media_type == "video" else data.get("photos", [])
            for item in items:
                if media_type == "video":
                    best = self._pick_best_video_quality(item.get("video_files", []))
                    if best:
                        results.append({
                            "url": best["link"],
                            "preview_url": item.get("image", ""),
                            "width": best.get("width", 0),
                            "height": best.get("height", 0),
                            "duration": item.get("duration"),
                            "author": item.get("user", {}).get("name", ""),
                            "source_url": item.get("url", ""),
                            "source": "pexels",
                            "api_tags": [item.get("user", {}).get("name", "pexels")],
                        })
                else:
                    src = item.get("src", {})
                    best_url = src.get("original", src.get("large2x", src.get("large", "")))
                    if best_url:
                        results.append({
                            "url": best_url,
                            "preview_url": src.get("medium", src.get("small", "")),
                            "width": item.get("width", 0),
                            "height": item.get("height", 0),
                            "duration": None,
                            "author": item.get("photographer", ""),
                            "source_url": item.get("url", ""),
                            "source": "pexels",
                            "api_tags": [item.get("photographer", "pexels")],
                        })
            return results
        except Exception as e:
            _log.warning("Pexels 搜索失败: %s", e)
            return []

    def _search_pixabay(self, query: str, media_type: str, per_page: int) -> list[dict]:
        if media_type == "video":
            url = PIXABAY_VIDEO_URL
        else:
            url = PIXABAY_PHOTO_URL

        params = {"key": self.pixabay_key, "q": query, "per_page": per_page}

        try:
            resp = httpx.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                _log.warning("Pixabay API 返回 %d: %s", resp.status_code, resp.text[:200])
                return []
            data = resp.json()

            results = []
            hits = data.get("hits", [])
            for hit in hits:
                api_tags = []
                tags_str = hit.get("tags", "")
                if tags_str:
                    api_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                user = hit.get("user", "")
                if user and user not in api_tags:
                    api_tags.append(user)

                if media_type == "video":
                    videos_data = hit.get("videos", {})
                    best = self._pick_best_video_quality_pixabay(videos_data)
                    if best:
                        results.append({
                            "url": best,
                            "preview_url": videos_data.get("medium", {}).get("url", ""),
                            "width": hit.get("videoWidth", 0) or 1920,
                            "height": hit.get("videoHeight", 0) or 1080,
                            "duration": hit.get("duration"),
                            "author": user,
                            "source_url": hit.get("pageURL", ""),
                            "source": "pixabay",
                            "api_tags": api_tags,
                        })
                else:
                    best_url = hit.get("largeImageURL", hit.get("webformatURL", ""))
                    if best_url:
                        results.append({
                            "url": best_url,
                            "preview_url": hit.get("previewURL", ""),
                            "width": hit.get("imageWidth", 0),
                            "height": hit.get("imageHeight", 0),
                            "duration": None,
                            "author": user,
                            "source_url": hit.get("pageURL", ""),
                            "source": "pixabay",
                            "api_tags": api_tags,
                        })
            return results
        except Exception as e:
            _log.warning("Pixabay 搜索失败: %s", e)
            return []

    @staticmethod
    def _pick_best_video_quality(files: list[dict]) -> Optional[dict]:
        if not files:
            return None
        quality_order = {"4k": 5, "uhd": 5, "hd": 3, "full_hd": 3, "sd": 2, "hls": 1}
        best = max(files, key=lambda f: quality_order.get(f.get("quality", "sd"), 0))
        return best

    @staticmethod
    def _pick_best_video_quality_pixabay(videos: dict) -> Optional[str]:
        for quality in ("large", "medium", "small"):
            item = videos.get(quality, {})
            if isinstance(item, dict) and item.get("url"):
                return item["url"]
            elif isinstance(item, str) and item:
                return item
        return None

    def download(self, url: str, dest_path: str, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        try:
            parent = os.path.dirname(dest_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            tmp_path = dest_path + ".tmp"

            with httpx.stream("GET", url, timeout=self.timeout, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    _log.warning("下载失败 HTTP %d: %s", resp.status_code, url)
                    return False

                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback(downloaded / total)

            if os.path.getsize(tmp_path) > 1024:
                os.replace(tmp_path, dest_path)
                _log.info("下载完成: %s (%d bytes)", dest_path, os.path.getsize(dest_path))
                return True
            else:
                _log.warning("下载文件过小: %s", tmp_path)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                return False
        except Exception as e:
            _log.warning("下载异常: %s", e)
            try:
                os.unlink(dest_path + ".tmp")
            except OSError:
                pass
            return False

    def search_and_download(
        self,
        queries: list[dict],
        assets_dir: str = "./assets",
        media_type: str = "video",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[str]:
        as_type = "video" if media_type == "video" else "image"
        subdir_map = {"video": "videos", "image": "images"}
        target_subdir = os.path.join(assets_dir, subdir_map.get(as_type, "videos"))

        downloaded: list[tuple[str, list[str]]] = []
        total = len(queries)

        for idx, q in enumerate(queries):
            if progress_callback:
                progress_callback(f"搜索: {q.get('query', '')}", idx / total)

            search_queries = expand_search_queries(
                q.get("keywords", []),
                style=q.get("style", ""),
                emotion=q.get("emotion", ""),
            )
            if not search_queries:
                search_queries = [q.get("query", "")]
            all_results = []
            for sq in search_queries:
                results = self.search(sq, media_type, per_page=self.max_per_query)
                all_results.extend(results)
                if len(all_results) >= self.max_per_query:
                    break

            if not all_results:
                _log.warning("未搜索到结果 (多词): %s", search_queries)
                if progress_callback:
                    progress_callback(f"未找到: {search_queries[0] if search_queries else q.get('query', '')}", (idx + 1) / total)
                continue

            best = all_results[0]
            seg_id = q.get("segment_id", idx + 1)
            base_name = _sanitize_filename(f"seg{seg_id:02d}_{q.get('query', 'media')[:40]}".strip("_"))

            url = best.get("url", "")
            if not url:
                continue

            ext = ".mp4" if media_type == "video" else ".jpg"
            dest_name = f"{base_name}{ext}"
            dest_path = os.path.join(target_subdir, dest_name)

            for attempt in range(3):
                msg = f"下载: {dest_name}"
                if attempt > 0:
                    msg += f" (重试{attempt})"
                if progress_callback:
                    progress_callback(msg, (idx + 0.3) / total)

                if self.download(url, dest_path):
                    downloaded.append((dest_path, best.get("api_tags", [])))
                    break
                else:
                    url = best.get("url", "")
            else:
                _log.warning("下载失败 (已重试3次): %s", dest_name)
                continue

            if progress_callback:
                progress_callback(f"完成: {dest_name}", (idx + 1) / total)

        _log.info("素材下载完成: %d/%d", len(downloaded), total)

        if downloaded:
            self._auto_scan([d[0] for d in downloaded], assets_dir)
            self._update_downloaded_tags(downloaded, assets_dir)

        return [d[0] for d in downloaded]

    def _update_downloaded_tags(self, downloaded_files: list[tuple[str, list[str]]], assets_dir: str):
        db_path = self._find_db_path(assets_dir)
        if not db_path:
            return
        try:
            db = Database(db_path)
            for path, api_tags in downloaded_files:
                if not api_tags:
                    continue
                asset = db.get_asset_by_file(os.path.basename(path))
                if asset:
                    merged = list(dict.fromkeys(asset.tags + api_tags))
                    db.update_asset_tags(asset.id, merged)
                    _log.info("更新标签: %s (%d tags)", os.path.basename(path), len(merged))
            db.close()
        except Exception as e:
            _log.warning("更新下载标签失败: %s", e)

    def _auto_scan(self, downloaded_files: list[str], assets_dir: str):
        db_path = self._find_db_path(assets_dir)
        if not db_path:
            db_path = "./database/clipforge.db"
        try:
            db = Database(db_path)
            db.init_tables()
            scanner = AssetScanner(db, assets_dir)
            before = db.get_asset_count().get("total", 0)
            scanner.scan_incremental()
            after = db.get_asset_count().get("total", 0)
            if after > before:
                _log.info("自动扫描完成: 新增 %d 个素材", after - before)
            db.close()
        except Exception as e:
            _log.warning("自动扫描失败: %s", e)

    def _find_db_path(self, assets_dir: str) -> Optional[str]:
        candidates = [
            os.path.join(os.path.dirname(assets_dir), "database", "clipforge.db"),
            os.path.join(assets_dir, "..", "database", "clipforge.db"),
            "./database/clipforge.db",
        ]
        for p in candidates:
            normalized = os.path.normpath(p)
            if os.path.exists(os.path.dirname(normalized)):
                return normalized
        return candidates[-1]
