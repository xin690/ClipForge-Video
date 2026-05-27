"""AI 规划模块（可选，默认关闭）

负责：
1. 素材选择：从 TopK 候选中推荐最佳匹配
2. 文案优化：优化口播文案
3. 主题规划：从主题文案生成完整视频脚本 + 素材搜索关键词
4. 搜索建议：为每个分段的素材匹配生成搜索查询

配置 ai.enabled: true 后使用。
"""

import json
import re
import logging
from typing import Optional
from core.models import Asset, Script, Segment

_log = logging.getLogger("ai_planner")


class AIPlanner:
    _API_URLS = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
    }

    _PLAN_SYSTEM_PROMPT = """你是一个短视频脚本策划专家。根据用户提供的主题，规划一个完整的视频脚本。

要求：
1. 将主题分解为3-6个视频段落
2. 每个段落包含口播文案(20-60字)、中文关键词标签(2-5个，用于匹配素材)、情绪、时长(4-8秒)
3. 生成英文搜索关键词(用于在素材网站搜索视频/图片)
4. 情绪可选: normal/strong/happy/sad/calm

请**只输出**以下JSON格式，不要包含```json标记或其他任何文字:
{"title":"视频标题","duration":数字,"segments":[{"id":1,"text":"口播文案","keywords":["关键词1","关键词2"],"emotion":"normal","duration":5,"search_query":"English search terms"},...]}"""

    def __init__(self, config: dict):
        ai_cfg = config.get("ai", {})
        self.enabled = ai_cfg.get("enabled", False)
        self.provider = ai_cfg.get("provider", "openai")
        self.api_key = ai_cfg.get("api_key", "")
        self.model = ai_cfg.get("model", "gpt-4o-mini")
        self.max_tokens = ai_cfg.get("max_tokens", 500)

    def _api_url(self) -> str:
        return self._API_URLS.get(self.provider, self._API_URLS["openai"])

    def _call_api(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> Optional[str]:
        if not self.enabled or not self.api_key:
            _log.warning("AI 未启用或 API Key 为空")
            return None
        try:
            import httpx
            response = httpx.post(
                self._api_url(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens or self.max_tokens,
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

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            return None
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None

    def plan_from_theme(self, theme: str, style: str = "knowledge") -> Optional[dict]:
        """从主题文案生成视频脚本 + 素材搜索关键词。

        Args:
            theme: 主题描述文案
            style: 视频风格 (knowledge/news/entertainment/commerce)

        Returns:
            dict with keys "script" (models.Script) and "search_queries" (list[dict]),
            搜索查询包含 segment_id/keywords/query/asset_type。
            失败返回 None。
        """
        user_prompt = f"主题: {theme}\n风格: {style}"
        max_retries = 3

        for attempt in range(max_retries):
            content = self._call_api(
                self._PLAN_SYSTEM_PROMPT,
                user_prompt,
                max_tokens=2000,
            )
            if content is None:
                return None

            data = self._extract_json(content)
            if data is None:
                _log.warning("AI 输出 JSON 解析失败 (第%d次), 原始输出: %s", attempt + 1, content[:200])
                user_prompt += "\n上次输出格式错误，请严格按照JSON格式重新输出。"
                continue

            segments_data = data.get("segments", [])
            if not segments_data:
                _log.warning("AI 未生成任何分段 (第%d次)", attempt + 1)
                user_prompt += "\nsegments不能为空，请生成至少3个分段。"
                continue

            search_queries = []
            clean_segments = []
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
                    "id": seg_id,
                    "text": text,
                    "keywords": [str(k).strip() for k in keywords if str(k).strip()],
                    "emotion": emotion if emotion in ("normal", "strong", "happy", "sad", "calm") else "normal",
                    "duration": duration,
                })

                search_queries.append({
                    "segment_id": seg_id,
                    "keywords": keywords,
                    "query": search_query,
                    "asset_type": "video",
                })

                total_duration += duration

            if not clean_segments:
                continue

            script_data = {
                "title": str(data.get("title", theme[:20])).strip() or theme[:20],
                "duration": total_duration,
                "style": style,
                "voice": "zh-CN-XiaoxiaoNeural",
                "bgm": "",
                "segments": clean_segments,
            }

            try:
                script = Script(**script_data)
            except Exception as e:
                _log.warning("Script 验证失败 (第%d次): %s", attempt + 1, e)
                user_prompt += f"\n上次数据验证失败: {e}。请修正数据。"
                continue

            _log.info("AI 脚本规划成功: %s (%d 段, %ds)", script.title, len(script.segments), script.duration)
            return {
                "script": script,
                "search_queries": search_queries,
            }

        _log.error("AI 规划失败，已重试 %d 次", max_retries)
        return None

    def suggest_search_queries(self, segments: list[Segment]) -> list[dict]:
        """为已有脚本的每个分段生成素材搜索关键词。

        Args:
            segments: 脚本分段列表

        Returns:
            list of {"segment_id": int, "query": str, "keywords": list[str], "asset_type": str}
        """
        if not segments:
            return []

        segment_texts = "\n".join(f"分段{seg.id}: {seg.text} (标签: {', '.join(seg.keywords)})" for seg in segments)

        system_prompt = """你是一个素材搜索助手。为视频脚本的每个分段生成英文搜索关键词，用于在素材网站(Pexels/Pixabay)搜索视频。
输出纯JSON数组，每个元素包含 segment_id 和 query:
[{"segment_id":1,"query":"mountain landscape drone china"},...]"""

        user_prompt = f"为以下视频脚本分段生成英文素材搜索关键词:\n{segment_texts}"

        content = self._call_api(system_prompt, user_prompt, max_tokens=500)
        if content is None:
            return []

        try:
            data = self._extract_json(content)
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
                    result.append({
                        "segment_id": seg_id,
                        "query": query,
                        "keywords": kw,
                        "asset_type": "video",
                    })
                return result
        except Exception as e:
            _log.warning("搜索关键词解析失败: %s", e)

        return [
            {"segment_id": seg.id, "query": " ".join(seg.keywords), "keywords": seg.keywords, "asset_type": "video"}
            for seg in segments
        ]

    def _api_select(self, text: str, candidates: list[Asset]) -> Optional[Asset]:
        if not candidates:
            return None
        try:
            import httpx
            system_prompt = "你是一个视频素材选择助手。根据文本内容，从候选中选择最匹配的素材文件。只返回文件名。"
            user_prompt = f"文本: {text}\n素材: {[a.file + ' (' + ','.join(a.tags) + ')' for a in candidates]}"
            response = httpx.post(
                self._api_url(),
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 50,
                },
                timeout=30,
            )
            data = response.json()
            chosen = data["choices"][0]["message"]["content"].strip()
            for asset in candidates:
                if asset.file in chosen or chosen in asset.file:
                    return asset
        except Exception:
            pass
        return candidates[0]

    def _api_optimize(self, text: str) -> str:
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
                    "max_tokens": self.max_tokens,
                },
                timeout=30,
            )
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return text
