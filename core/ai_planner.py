"""AI 规划模块（可选，默认关闭）
⚠ 未集成：此模块当前未在任何管线中调用，为预留功能。

负责：
1. 素材选择：从 TopK 候选中推荐最佳匹配
2. 文案优化：优化口播文案
3. 节奏规划：建议镜头时长

配置 ai.enabled: true 后使用（集成时需在 pipeline.py 中调用）。
"""

from typing import Optional
from core.models import Asset


class AIPlanner:
    _API_URLS = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
    }

    def __init__(self, config: dict):
        ai_cfg = config.get("ai", {})
        self.enabled = ai_cfg.get("enabled", False)
        self.provider = ai_cfg.get("provider", "openai")
        self.api_key = ai_cfg.get("api_key", "")
        self.model = ai_cfg.get("model", "gpt-4o-mini")
        self.max_tokens = ai_cfg.get("max_tokens", 500)

    def _api_url(self) -> str:
        return self._API_URLS.get(self.provider, self._API_URLS["openai"])

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
