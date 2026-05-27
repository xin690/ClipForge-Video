# ClipForge v2 效果增强计划

> 当前版本 CLIForge 已完成 AI 规划 + 自动下载 + 配音选择 等核心功能。
> v2 目标：聚焦视频本身的视觉和听觉品质，让输出视频更专业、更美观。

---

## 总体路线

| 批次 | 内容 | 主线 | 预估代码量 |
|------|------|------|-----------|
| **第一批** | ① 增强转场 + ② 暗角调色 + ③ 音频闪避 | 核心视听体验升级 | ~100 行 |
| **第二批** | ④ Intro/Outro 片头片尾 + ⑤ 关键词高亮字幕 | 包装呈现 | ~100 行 |
| **第三批** | ⑥ 竖屏 9:16 + 竖屏适配模式 | 多平台适配 | ~30 行 |

各批之间无代码依赖，可按任意顺序开发。

---

## 第一批 — 核心视听体验升级

### ① 增强转场

**涉及文件**: `core/ffmpeg.py` `core/rules.py`

当前管线只支持 `cut` / `fade` / `slide` 三种转场，且 xfade 映射表只有 3 条。

**改动 1 — ffmpeg.py**: 扩展 XFADE_MAP 到 10+ 种

```python
XFADE_MAP = {
    "dissolve":   "dissolve",
    "fade":       "fade",
    "fadeblack":  "fadeblack",
    "fadewhite":  "fadewhite",
    "circleopen": "circleopen",
    "radial":     "radial",
    "zoomin":     "zoomin",
    "slide":      "slideleft",
    "smoothleft": "smoothleft",
    "pixelize":   "pixelize",
    "horzopen":   "horzopen",
}
```

新增 `XFADE_DURATION` 映射（不同类型不同时长）：

```python
XFADE_DURATION = {
    "cut": 0.0, "fade": 0.4, "dissolve": 0.5,
    "circleopen": 0.6, "fadeblack": 0.5,
    "pixelize": 0.6, "zoomin": 0.5,
}
```

**改动 2 — rules.py**: 按相邻片段情绪组合选择转场

| 前一片段 | → | 后一片段 | 转场 |
|----------|---|----------|------|
| normal | → | normal | dissolve |
| normal | → | strong | fade |
| normal | → | calm | fadeblack |
| strong | → | strong | circleopen |
| strong | → | calm | fade |
| calm | → | normal | fadewhite |
| calm | → | calm | dissolve |
| 任一 | (短片段 < 3s) | | cut |

### ② 暗角 + 调色

**涉及文件**: `core/renderer.py` `core/pipeline.py`

**改动 1 — renderer.py**: 新增 `COLOR_PRESETS` 类常量

```python
COLOR_PRESETS = {
    "knowledge":     "eq=brightness=0.03:contrast=1.10:saturation=1.05,vignette=PI/4",
    "news":          "eq=brightness=0.05:contrast=1.15:saturation=0.90,vignette=PI/5",
    "entertainment": "eq=brightness=0.04:contrast=1.05:saturation=1.20,vibrance=intensity=0.3",
    "commerce":      "vibrance=intensity=0.3,eq=contrast=1.10,vignette=PI/4.5",
}
```

**改动 2 — Renderer.render()**: 接受 `style: str = "knowledge"` 参数，传入 `_render_clip_with_asset()`

**改动 3 — _render_clip_with_asset()**: 在 `vf_full` 滤镜链末尾追加 `COLOR_PRESETS[style]`

**改动 4 — pipeline.py**: `renderer.render()` 调用时传入 `style=script.style`

效果：Pexels 来源不同的素材视觉风格统一，所有片段带电影感暗角。

### ③ 音频闪避 (Audio Ducking)

**涉及文件**: `core/renderer.py`

**改动 — _mix_bgm_audio()**: 从简单混音改为侧链压缩

```
当前: [1:a]volume={bgm_vol}[bgm];[0:a][bgm]amix=inputs=2:duration=longest[a]
改为: [voice]aformat=... [bgm]aformat=... ;
      [voice][bgm]sidechaincompress=threshold=0.02:ratio=12:attack=50:release=500[sc] ;
      [voice][sc]amix=inputs=2:duration=first:weights='1 0.3'[a]
```

- `threshold=0.02`: 人声 > -34dB 时触发闪避
- `ratio=12`: BGM 音量压 12 倍
- `attack=50ms`: 人声出现后 50ms 开始压低
- `release=500ms`: 人声结束后 500ms 平滑恢复
- 最终混合：人声 100% + 压缩后 BGM 30%

可选：将 ducking 参数加入 config（`bgm.ducking_threshold`, `bgm.ducking_ratio` 等）。

---

## 第二批 — 包装呈现

### ④ Intro/Outro 片头片尾

**涉及文件**: `core/renderer.py`

**改动 1 — _generate_title_card(title, style, duration=3)**: 用 FFmpeg `color` + `drawtext` 生成动画标题

```bash
ffmpeg -f lavfi -i "color=c=#1a1a2e:s=1920x1080:d=3" \
  -vf "drawtext=text='{title}':fontsize=64:fontcolor=white: \
        alpha='min(1,t/2)':x=(w-text_w)/2:y=(h-text_h)/2"
```

- 背景色按 `style` 变化（knowledge=深蓝, news=深红, entertainment=紫, commerce=橙）
- 标题文字 2s 淡入，停留 1s
- 底部小字 "Powered by ClipForge AI"

**改动 2 — _generate_outro_card(duration=3)**: 类似生成片尾

- 黑色背景 + "感谢观看" + "制作: ClipForge AI"
- 文字从下往上滚动或淡入

**改动 3 — render() 集成**: 在 concat 阶段将卡片添加到 clip 列表

```
clip_files = [intro_path] + clip_files + [outro_path]
# transitions 列表前后追加对应转场
```

- intro→clip1: 用 fade
- last_clip→outro: 用 fade

### ⑤ 关键词高亮字幕

**涉及文件**: `core/subtitle.py`

**改动 — _format_ass()**: 对对话文本中的特定模式应用 ASS 颜色标签

```python
HIGHLIGHT_RULES = [
    (r"\d+(\.\d+)?%",     "{\\c&H00D7FF&}"),   # 百分比 → 金色
    (r"https?://\S+",     "{\\c&HFFAA00&}"),   # 链接 → 蓝色
    (r"\b\d+(\.\d+)?\b",  "{\\c&H00FFFF&}"),   # 纯数字 → 黄色
    (r"[\u4e00-\u9fff]{2,6}(?:公司|机构|大学|研究所)", "{\\c&H00FF88&}"),  # 机构名 → 青色
]
```

处理逻辑：
1. 对每段 ASS 对话文本按规则顺序扫描
2. 匹配到的片段用 `{\c&H...&}` 着色，用 `{\c}` 恢复默认色
3. 注意规则间的嵌套优先级（百分比优先于纯数字）

---

## 第三批 — 多平台适配

### ⑥ 竖屏 9:16 输出

**涉及文件**: `ui/settings_dialog.py`

**改动 — settings_dialog.py**: 在分辨率下拉菜单追加 `1080x1920 (竖屏)`

当前渲染器已自动适应分辨率：
- `scale=1080:1920:force_original_aspect_ratio=decrease` 保证不拉伸
- `pad=1080:1920:(ow-iw)/2:(oh-ih)/2` 用黑边填充

**竖屏适配模式（后续可扩展）**:

在 config 中新增 `video.portrait_fit` 字段（默认 `"pad"`）：

| 模式 | 效果 | 适用场景 |
|------|------|----------|
| `pad` | 居中 + 黑边 | 通用，不裁切内容 |
| `crop` | 放大填满画面，裁切左右 | 需要全屏填充 |
| `scale` | 强制拉伸填满 | 画面比例不敏感 |

实现：在 `_build_camera_filter()` 中根据 `portrait_fit` 分支处理。

---

## 文件变更总览

| 文件 | 第一批 | 第二批 | 第三批 | 总计(行) |
|------|--------|--------|--------|----------|
| `core/ffmpeg.py` | ~20 | - | - | ~20 |
| `core/rules.py` | ~30 | - | - | ~30 |
| `core/renderer.py` | ~60 | ~80 | - | ~140 |
| `core/subtitle.py` | - | ~30 | - | ~30 |
| `core/pipeline.py` | ~5 | - | - | ~5 |
| `ui/settings_dialog.py` | - | - | ~10 | ~10 |
| **合计** | **~115** | **~110** | **~10** | **~235** |

零新增第三方依赖，全部使用 FFmpeg 内置滤镜。

---

## 以下回原方案的可行性

本计划中未包含的调研项及原因：

| 方案 | 未列入原因 |
|------|-----------|
| Karaoke 逐词高亮 | 需要 Whisper 词级时间戳，依赖较重，适合 v3 |
| 人脸追踪动态缩放 | 需要 mediapipe，知识类视频收益有限 |
| 节拍检测对齐 | 需要 librosa，知识类视频节奏平缓 |
| 分屏/PiP | 不适合当前的知识/新闻类模板 |
| 粒子/故障效果 | 风格化过强 |
| 录屏光标高亮 | 仅录屏场景有用 |

---

## 版本记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-05-27 | v1 | 初始规划文档，6 项 enhancement |
