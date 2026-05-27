# ClipForge AI 规划 v3 — 实施总结

**状态**: 全部完成，168/168 测试通过  
**提交**: v3 overhaul (`f03e979`) + target duration (`7240be9`) + QA module (`0b43f8d`)

---

## v3 变更总览

### 1. Token 预算彻底删除

| 改动 | 原因 |
|------|------|
| 删除 `TokenBudget` 整个类 | `max_per_session` 硬限制可能截断 AI 输出，影响效果 |
| 删除所有 `_call_api` 的 `max_tokens` 参数 | 不限制模型输出长度，保证完整 JSON |
| 删除 L4 预算检查 + L6 压缩 | 对应逻辑不再需要 |
| 删除 `token_guard` 配置段 | 简化配置 |
| 仅靠 `max_versions=2` 控制总调用次数 | 最多 5 次 API 调用，成本可忽略 |

### 2. 自动 critique-revise 循环移除

`plan_from_theme_v2` 从 5 次 API 调用减为 1 次：

- **之前**: plan → critique → revise → critique → revise
- **之后**: plan → 直接返回（单次调用）

用户可通过以下手动方式迭代：
- **优化提示词** — AI 扩展用户的主题文案
- **重新规划** — 丢弃当前结果重新生成
- **润色该段** — AI 优化单段口播文案

### 3. 素材配选 + 预览审核 Tab → 脚本预览 Tab

| 删除 | 新增 |
|------|------|
| 素材配选 tab（选片不流入 Pipeline） | 脚本预览 tab（QTextBrowser，HTML 格式化展示） |
| 预览审核 tab（反馈不重渲染） | |
| 8 个相关方法（~260 行） | `_show_script_preview()` |
| 13 个未使用 import | |

### 4. 配音 + BGM AI 推荐

- Prompt 新增 voice/bgm 输出要求，JSON 格式扩展
- AI 根据风格/情绪推荐 5 种 edge-tts 角色
- 脚本编辑 tab 标题行显示配音角色 + BGM 信息

### 5. v2 基建设施保留

以下功能保持原样不变：

- **CachedPlanner** — 缓存 API 响应，避免重复调用
- **Matcher** — 类型感知权重评分（STYLE_WEIGHTS）
- **EMOTION_ALIASES** — 情绪别名映射
- **scanner 标签增强** — 数字过滤、英文停用词、父目录去重
- `_extract_json` — 支持 markdown 代码块
- `_validate_input` or 短路修复

---

## 配置

`config.yaml` 的 `ai` 段精简为：

```yaml
ai:
  enabled: false
  provider: openai
  api_key: ""
  model: gpt-4o-mini
  max_versions: 2
  critique_enabled: true
```

`token_guard` 已删除。

---

## 规划流程

```
用户输入主题
    │
    ▼
[优化提示词] ── AI 扩展主题 → 回填 theme_edit（可选）
    │
    ▼
[AI 规划] ── plan_from_theme 单次调用
    │
    ▼
脚本编辑 Tab         脚本预览 Tab
  - 7 列表格          - HTML 展示完整脚本
  - 版本选择器         - 标题/风格/配音/BGM
  - 润色/重规划        - 每段详情
    │
    ▼
[润色该段] ─ AI 局部优化文案
[重新规划] ─ 清空结果重新生成
[保存脚本] ─ 导出 JSON
[下载素材] ─ 根据搜索词下载
[内容检查] ─ 10 项自动化脚本质检 / 预设切换 / 重新检查
```

---

## 相关文件

| 文件 | 角色 |
|------|------|
| `core/ai_planner.py` | 核心规划：plan_from_theme、optimize_theme |
| `core/matcher.py` | 素材匹配：类型感知权重 |
| `core/config.py` | 配置默认值 |
| `config.template.yaml` | 配置模板 |
| `ui/ai_plan_dialog.py` | 对话框：脚本编辑 + 脚本预览 + 内容检查三 Tab |
| `core/scanner.py` | 素材扫描：标签增强 |
| `core/timeline.py` | 时间线构建：传入 script.style |
| `tests/test_ai_planner.py` | 更新测试适配 |
