"""AI 规划模块（可选，默认关闭）

负责：
1. 素材选择：从 TopK 候选中推荐最佳匹配
2. 文案优化：优化口播文案
3. 主题规划：从主题文案生成完整视频脚本 + 素材搜索关键词
4. 搜索建议：为每个分段的素材匹配生成搜索查询
5. 自审迭代：AI 生成后自我评审并改进（v2）

配置 ai.enabled: true 后使用。
"""

import json
import re
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional
from core.config import get_config
from core.models import Asset, Script, Segment

_log = logging.getLogger("ai_planner")

_AI_CACHE_DIR = Path("./cache/ai")


class CachedPlanner:
    """缓存包装器：相同输入跳过 AI API 调用。"""

    _CACHE_TTL = {
        "plan": 604800,       # 7 天
        "critique": 3600,     # 1 小时
        "search_query": 604800,
        "duration": 604800,   # 7 天
    }

    @staticmethod
    def _cache_key(data: dict, cache_type: str) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return f"{cache_type}_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"

    @staticmethod
    def get(cache_type: str, data: dict) -> Optional[str]:
        key = CachedPlanner._cache_key(data, cache_type)
        path = _AI_CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            ttl = CachedPlanner._CACHE_TTL.get(cache_type, 3600)
            if time.time() - entry["ts"] < ttl:
                return entry["response"]
        except Exception:
            pass
        return None

    @staticmethod
    def set(cache_type: str, data: dict, response: str):
        _AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = CachedPlanner._cache_key(data, cache_type)
        path = _AI_CACHE_DIR / f"{key}.json"
        try:
            path.write_text(json.dumps({"ts": time.time(), "response": response}, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            _log.warning("缓存写入失败: %s", e)

    @staticmethod
    def invalidate_for_segment(seg_id: int):
        for f in _AI_CACHE_DIR.glob("*.json"):
            if f"seg_{seg_id}" in f.stem:
                f.unlink()

    @staticmethod
    def invalidate_all():
        for f in _AI_CACHE_DIR.glob("*.json"):
            f.unlink()


EMOTION_ALIASES = {
    "excited": "strong", "passionate": "strong", "intense": "strong",
    "joyful": "happy", "cheerful": "happy", "playful": "happy",
    "thoughtful": "calm", "peaceful": "calm", "serene": "calm",
    "melancholic": "sad", "nostalgic": "sad", "emotional": "sad",
}


class AIPlanner:
    _API_URLS = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
    }

    _PLAN_SYSTEM_PROMPT = """你是一个短视频剧本策划专家。根据用户提供的主题和风格，规划一个完整的视频剧本。

要求：
1. 【分段落】将主题分解为3-6个视频段落，每段聚焦一个子观点
2. 【文案】每段口播文案20-60字，语言口语化、适合配音
3. 【关键词】每段2-5个英文关键词标签（用于匹配本地素材文件名和标签），**与相邻段的关键词不应雷同**
4. 【情绪】为每段指定情绪，**相邻段落不应使用相同情绪**：
   - normal: 中性叙述
   - strong: 强调/激动
   - happy: 轻松/愉悦
   - sad: 感动/思考
   - calm: 平静/总结
5. 【时长】总时长控制在目标时长附近（误差允许 ±10 秒），各段 4-10 秒且有**长短节奏变化**
6. 【搜索词】为每段生成英文搜索关键词（用于Pexels/Pixabay搜索视频素材）
7. 【情绪曲线】全片应有情绪起伏：开头吸引注意→中间充实内容→结尾感悟/号召
8. 【配音】根据影片风格和情绪曲线，推荐最适合的 edge-tts 配音角色:
   - zh-CN-XiaoxiaoNeural: 女声温暖亲切，适合知识科普/通用
   - zh-CN-YunxiNeural: 男声沉稳可靠，适合知识科普/新闻
   - zh-CN-XiaoyiNeural: 女声活泼热情，适合娱乐/电商
   - zh-CN-YunyangNeural: 男声激昂有力，适合电商/宣传
   - zh-CN-YunjianNeural: 男声专业清晰，适合新闻资讯
9. 【背景音乐】根据影片风格推荐 BGM 类型（如"轻快""舒缓""激昂""温馨""科技感""自然"等），用中文描述

请**只输出**以下JSON格式，不要包含```json标记或其他任何文字:
{"title":"视频标题","duration":总秒数,"voice":"zh-CN-XiaoxiaoNeural","bgm":"舒缓","segments":[{"id":1,"text":"口播文案","keywords":["关键词1","关键词2"],"emotion":"normal","duration":5,"search_query":"English search terms"},...]}"""

    def __init__(self, config: dict):
        ai_cfg = config.get("ai", {})
        self.enabled = ai_cfg.get("enabled", False)
        self.provider = ai_cfg.get("provider", "openai")
        self.api_key = ai_cfg.get("api_key", "")
        self.model = ai_cfg.get("model", "gpt-4o-mini")
        self.critique_enabled = ai_cfg.get("critique_enabled", True)
        self.max_versions = ai_cfg.get("max_versions", 2)
        self._debounce_seconds = 3.0
        self._last_call_time = 0.0

    def _api_url(self) -> str:
        return self._API_URLS.get(self.provider, self._API_URLS["openai"])

    def _call_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self.enabled or not self.api_key:
            _log.warning("AI 未启用或 API Key 为空")
            return None
        # 防抖
        now = time.time()
        if now - self._last_call_time < self._debounce_seconds:
            _log.warning("操作过于频繁，跳过")
            return None
        self._last_call_time = now
        try:
            import httpx
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}]
            response = httpx.post(
                self._api_url(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                },
                timeout=60,
            )
            if response.status_code != 200:
                _log.error("AI API 返回非200: %d %s", response.status_code, response.text[:200])
                return None
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content
        except Exception as e:
            _log.error("AI API 调用失败: %s", e)
            return None

    def _cached_call(self, cache_type: str, system_prompt: str,
                     user_prompt: str, cache_data: dict) -> Optional[str]:
        """缓存优先的 API 调用。"""
        cached = CachedPlanner.get(cache_type, cache_data)
        if cached is not None:
            _log.debug("缓存命中: %s/%s", cache_type, cache_data.get("_label", ""))
            return cached
        content = self._call_api(system_prompt, user_prompt)
        if content:
            CachedPlanner.set(cache_type, cache_data, content)
        return content

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if not json_match:
            return None
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_json_list(text: str) -> Optional[list]:
        list_match = re.search(r'\[[\s\S]*\]', text)
        if not list_match:
            return None
        try:
            return json.loads(list_match.group())
        except json.JSONDecodeError:
            return None

    # ── L1: 前置拦截 ─────────────────────────────────────

    def _validate_input(self, input_type: str, data: dict) -> list[str]:
        errors = []
        segs = data.get("segments", data.get("script", {}).get("segments", []))
        if input_type == "theme":
            theme = data.get("theme", "").strip()
            if len(theme) < 3:
                errors.append("主题描述过短")
        elif input_type in ("critique", "revise"):
            if not segs:
                errors.append("分段为空")
            for seg in segs:
                text = str(seg.get("text", "")).strip()
                if len(text) < 5:
                    errors.append(f"段{seg.get('id')} 文案过短 ({len(text)}字)")
                if len(text) > 200:
                    errors.append(f"段{seg.get('id')} 文案过长 ({len(text)}字)")
        elif input_type == "optimize":
            text = data.get("text", "").strip()
            if len(text) < 5 or len(text) > 200:
                errors.append("文案长度需 5~200 字")
        elif input_type == "select":
            if not data.get("candidates"):
                errors.append("候选列表为空")
        return errors

    # ── L3: 自审循环 ─────────────────────────────────────

    def _sanitize_segments(self, segments_data: list[dict]) -> tuple[list[dict], list[dict], int]:
        clean_segments = []
        search_queries = []
        total_duration = 0
        for i, seg in enumerate(segments_data):
            seg_id = seg.get("id", i + 1)
            text = str(seg.get("text", "")).strip()
            keywords = seg.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]
            emotion = seg.get("emotion", "normal")
            duration = seg.get("duration", 5)
            if not isinstance(duration, (int, float)) or duration < 2:
                duration = 5
            duration = min(int(duration), 15)

            search_query = str(seg.get("search_query", "")).strip()
            if not search_query and keywords:
                search_query = " ".join(keywords)

            clean_segments.append({
                "id": seg_id, "text": text,
                "keywords": [str(k).strip() for k in keywords if str(k).strip()],
                "emotion": EMOTION_ALIASES.get(emotion, emotion)
                    if emotion in ("normal", "strong", "happy", "sad", "calm") else "normal",
                "duration": duration,
            })
            search_queries.append({
                "segment_id": seg_id, "keywords": keywords,
                "query": search_query, "asset_type": "video",
            })
            total_duration += duration
        return clean_segments, search_queries, total_duration

    def _critique_script(self, script_data: dict) -> list[str]:
        """AI 自审。L1 拦截 + L2 缓存。"""
        errors = self._validate_input("critique", script_data)
        if errors:
            return errors

        if not self.critique_enabled:
            return []

        cache_data = {"script": script_data, "model": self.model}
        content = self._cached_call(
            "critique",
            """你是短视频剧本质量评审专家。评审以下剧本，指出问题。

评审维度：
1. 关键词密度：每段至少2个关键词，相邻段不应雷同
2. 情绪变化：相邻段落不应同情绪，全片应有起伏
3. 时长分布：不应所有段相同时长，应有长短变化
4. 文案质量：文字是否口语化、易懂
5. 搜索词：英文搜索词是否具体、可搜索

**输出格式要求**：每行一个"- 问题描述"，不得输出其他文字。
如果没有问题，只输出一行："无" """,
            f"剧本:\n{json.dumps(script_data, ensure_ascii=False, indent=2)}",
            cache_data,
        )
        if not content:
            return []
        issues = [line.strip("- ").strip() for line in content.split("\n")
                  if line.strip().startswith("-")]
        real = [i for i in issues if i not in ("无", "")]
        # 一次不改超过 4 个问题
        return real[:4]

    def _revise_script(self, script_data: dict, critiques: list[str]) -> Optional[dict]:
        """根据评审意见改进剧本。L1 拦截。"""
        if not critiques:
            return None
        critiques_text = "\n".join(f"- {c}" for c in critiques)
        content = self._call_api(
            """你是短视频剧本编辑。根据用户提供的批评意见，改进以下剧本。

规则：
1. 保留整体结构和所有分段，只修改批评意见指出的问题
2. 输出**完整**的 JSON 对象，包含 title、duration、segments
3. 每个 segment 必须包含：id、text、keywords、emotion、duration、search_query
4. 未指出的字段保持原值不变
5. **只输出 JSON，不要包含 ```json 标记或其他文字**""",
            f"原剧本:\n{json.dumps(script_data, ensure_ascii=False, indent=2)}\n\n批评意见:\n{critiques_text}",
        )
        if not content:
            return None
        return self._extract_json(content)

    def _apply_feedback(self, script_dict: dict, feedback_list: list) -> Optional[dict]:
        """根据用户反馈调整脚本。仅在需要时调 AI。"""
        problematic = [f for f in feedback_list if "👎" in f.get("rating", "")]
        if not problematic:
            return None
        # 去重
        seen = set()
        unique = []
        for f in problematic:
            key = (f.get("segment_id"), str(f.get("note", ""))[:20])
            if key not in seen:
                seen.add(key)
                unique.append(f)
        # 仅节奏问题 → 本地调时长
        only_pacing = all("时长" in f.get("note", "") or "节奏" in f.get("note", "") for f in unique)
        if only_pacing:
            for seg in script_dict.get("segments", []):
                seg["duration"] = max(3, min(10, seg["duration"] - 1))
            return script_dict
        return None

    def _validate_before_api(self, data: dict) -> list[str]:
        return self._validate_input("critique", data)

    # ── 核心入口 ────────────────────────────────────────

    def plan_from_theme(self, theme: str, style: str = "knowledge", target_duration: int = 0) -> Optional[dict]:
        """从主题文案生成视频脚本 + 素材搜索关键词。

        Args:
            theme: 视频主题文案
            style: 视频风格
            target_duration: 目标总时长（秒），0 表示不限制

        Returns:
            dict with keys "script" (Script) and "search_queries" (list[dict])。
            失败返回 None。
        """
        user_prompt = f"主题: {theme}\n风格: {style}"
        if target_duration > 0:
            user_prompt += f"\n目标时长: {target_duration}秒"
        max_retries = 3

        for attempt in range(max_retries):
            content = self._call_api(self._PLAN_SYSTEM_PROMPT, user_prompt)
            if content is None:
                return None

            data = self._extract_json(content)
            if data is None:
                _log.warning("JSON 解析失败 (第%d次)", attempt + 1)
                user_prompt += "\n上次输出格式错误，请严格按照JSON格式重新输出。"
                continue

            segments_data = data.get("segments", [])
            if not segments_data:
                _log.warning("分段为空 (第%d次)", attempt + 1)
                user_prompt += "\nsegments不能为空，请生成至少3个分段。"
                continue

            clean_segments, search_queries, total_duration = self._sanitize_segments(segments_data)
            if not clean_segments:
                continue

            _VOICES = {"zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-XiaoyiNeural",
                       "zh-CN-YunyangNeural", "zh-CN-YunjianNeural"}
            voice = str(data.get("voice", "zh-CN-XiaoxiaoNeural")).strip()
            if voice not in _VOICES:
                voice = "zh-CN-XiaoxiaoNeural"
            bgm = str(data.get("bgm", "")).strip()
            script_data = {
                "title": str(data.get("title", theme[:20])).strip() or theme[:20],
                "duration": total_duration, "style": style,
                "voice": voice, "bgm": bgm,
                "segments": clean_segments,
            }
            try:
                script = Script(**script_data)
            except Exception as e:
                _log.warning("Script 验证失败 (第%d次): %s", attempt + 1, e)
                user_prompt += f"\n上次数据验证失败: {e}。请修正数据。"
                continue

            _log.info("AI 脚本规划成功: %s (%d 段, %ds)", script.title, len(script.segments), script.duration)
            return {"script": script, "search_queries": search_queries}

        _log.error("AI 规划失败，已重试 %d 次", max_retries)
        return None

    def _estimate_segment_durations(self, script: Script) -> Script:
        voice = script.voice or "zh-CN-XiaoxiaoNeural"
        cfg = get_config()
        speed = cfg.get("tts", {}).get("speed", 1.0)
        total = 0
        for seg in script.segments:
            try:
                from core.tts import preview_duration
                tts_dur = preview_duration(seg.text, voice, speed)
                seg.duration = max(int(round(tts_dur)), seg.duration)
            except Exception:
                pass
            total += seg.duration
        script.duration = total
        return script

    def plan_from_theme_v2(self, theme: str, style: str = "knowledge", target_duration: int = 0) -> Optional[dict]:
        result = self.plan_from_theme(theme, style, target_duration=target_duration)
        if not result:
            return None

        script = result["script"]
        script = self._estimate_segment_durations(script)
        search_queries = result["search_queries"]

        return {
            "script": script,
            "search_queries": search_queries,
            "versions": [{"script": script.model_dump(), "critiques": []}],
        }

    # ── 已有的辅助方法 ──────────────────────────────────

    def suggest_search_queries(self, segments: list[Segment]) -> list[dict]:
        if not segments:
            return []
        if not self.enabled or not self.api_key:
            return []
        segment_texts = "\n".join(f"分段{seg.id}: {seg.text} (标签: {', '.join(seg.keywords)})" for seg in segments)
        system_prompt = """你是一个素材搜索助手。为视频脚本的每个分段生成英文搜索关键词，用于在素材网站(Pexels/Pixabay)搜索视频。
输出纯JSON数组，每个元素包含 segment_id 和 query:
[{"segment_id":1,"query":"mountain landscape drone china"},...]"""
        user_prompt = f"为以下视频脚本分段生成英文素材搜索关键词:\n{segment_texts}"
        content = self._cached_call(
            "search_query",
            system_prompt, user_prompt,
            {"segments": [s.model_dump() for s in segments], "model": self.model},
        )
        if content:
            data = self._extract_json_list(content)
            if isinstance(data, list):
                result = []
                for item in data:
                    seg_id = item.get("segment_id", len(result) + 1)
                    query = item.get("query", "").strip()
                    kw = []
                    for seg in segments:
                        if seg.id == seg_id:
                            kw = seg.keywords
                            break
                    result.append({"segment_id": seg_id, "query": query, "keywords": kw, "asset_type": "video"})
                return result
        return [{"segment_id": seg.id, "query": " ".join(seg.keywords), "keywords": seg.keywords, "asset_type": "video"} for seg in segments]

    def _api_select(self, text: str, candidates: list[Asset]) -> Optional[Asset]:
        if self._validate_input("select", {"text": text, "candidates": candidates}):
            return candidates[0] if candidates else None
        try:
            import httpx
            system_prompt = "你是一个视频素材选择助手。根据文本内容，从候选中选择最匹配的素材文件。只返回文件名。"
            user_prompt = f"文本: {text}\n素材: {[a.file + ' (' + ','.join(a.tags) + ')' for a in candidates]}"
            response = httpx.post(
                self._api_url(),
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={                "model": self.model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]},
                timeout=30,
            )
            data = response.json()
            chosen = data["choices"][0]["message"]["content"].strip()
            for asset in candidates:
                if asset.file in chosen or chosen in asset.file:
                    return asset
        except Exception:
            pass
        return candidates[0] if candidates else None

    def _api_optimize(self, text: str) -> str:
        errors = self._validate_input("optimize", {"text": text})
        if errors:
            return text
        try:
            import httpx
            response = httpx.post(
                self._api_url(),
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个文案润色助手。优化以下口播文案，使其更自然流畅。直接输出优化后的文本。"},
                        {"role": "user", "content": text},
                    ],
                },
                timeout=30,
            )
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return text

    def optimize_theme(self, theme: str, style: str = "knowledge") -> Optional[str]:
        """用 AI 扩展/优化视频主题描述，返回优化后的提示词或 None。"""
        if not self.enabled or not self.api_key:
            return None
        system_prompt = """你是一个短视频策划助手。根据用户提供的主题和风格，扩展为详细、具体的视频策划提示词。

要求：
1. 保留用户原始意图
2. 补充具体的内容方向、可参考的画面、预期的情绪基调
3. 用中文输出，50-100字
4. 直接输出优化后的提示词，不要包含解释或其他文字"""
        user_prompt = f"主题: {theme}\n风格: {style}"
        content = self._call_api(system_prompt, user_prompt)
        if content and len(content) > len(theme):
            return content.strip()
        return None

    def _score_emotion_match(self, text: str, assets: list[list[Asset]]) -> list[float]:
        scores = []
        text_list = text if isinstance(text, list) else [text]
        try:
            system_prompt = "你是情绪分析专家。判断每段文案与对应素材的情绪匹配度(0-100)，只返回空格分隔的数字列表。"
            lines = []
            for i, seg_assets in enumerate(assets):
                if i >= len(text_list):
                    break
                tags_str = "; ".join(", ".join(a.tags) for a in seg_assets[:3])
                lines.append(f"段{i}: 文案=\"{text_list[i]}\" 素材标签=\"{tags_str}\"")
            user_prompt = "\n".join(lines)
            content = self._cached_call(
                "emotion_match",
                system_prompt, user_prompt,
                {"segments": lines, "model": self.model},
            )
            if content:
                nums = re.findall(r"\d+", content)
                scores = [float(n) / 100.0 for n in nums[:len(assets)]]
        except Exception:
            pass
        while len(scores) < len(assets):
            scores.append(0.5)
        return scores[:len(assets)]
