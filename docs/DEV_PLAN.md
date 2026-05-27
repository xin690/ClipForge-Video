# ClipForge 完整开发计划文档

> 基于 `lightweight_ai_video_studio_architecture_cn.md` 架构方案
> 目标：开发可实际运行的 Windows 桌面端成品软件

---

## 目录

1. [项目概述](#1-项目概述)
2. [开发环境与依赖](#2-开发环境与依赖)
3. [项目目录结构](#3-项目目录结构)
4. [分阶段开发计划](#4-分阶段开发计划)
5. [关键模块设计决策](#5-关键模块设计决策)
6. [测试步骤详细设计](#6-测试步骤详细设计)
7. [交付物清单](#7-交付物清单)
8. [风险与缓释](#8-风险与缓释)
9. [免费素材获取建议](#9-免费素材获取建议)

---

## 实际实施状态总结

> 最后更新：2026-05-27 | 168/168 测试通过 | AI 内容规划 + 素材自动下载 + 内容质检（QA） 完成

### 项目状态

| 项目 | 状态 | 说明 |
|---|---|---|
| 所有 16 个核心模块 | ✅ 完成 | models, config, database, scanner, matcher, rules, timeline, tts, subtitle, renderer, ffmpeg, pipeline, ai_planner, downloader, script, qa |
| 所有 10 个 GUI 模块 | ✅ 完成 | main_window, theme, settings_dialog, script_editor, asset_browser, timeline_view, preview_panel, batch_panel, ai_plan_dialog |
| 测试 | ✅ 168/168 通过 | 17 个测试文件，覆盖所有核心模块（含 AI 规划 + 下载器 + QA） |
| 端到端渲染 | ✅ 通过 | `e2e_render.py` 输出 24s MP4（H.264 + AAC + 硬字幕 + BGM） |
| FFmpeg | ✅ 全量版 | C:\ffmpeg\bin，支持 libass/vpx/x265/opus 等全部滤镜 |
| xfade 转场 | ✅ 实现 | cut/fade/slide 转场，concat demuxer + xfade 滤镜链 |
| loudnorm 响度归一化 | ✅ 实现 | EBU R128 标准（I=-16, TP=-1.5, LRA=11） |
| AI 内容规划 | ✅ 实现 | 主题→AI 生成 Script + 搜索关键词 → 程序下载素材 → 自动扫描 |
| 素材自动下载 | ✅ 实现 | Pexels/Pixabay API 搜索 + httpx 流式下载 + 增量扫描 |
| 运镜效果 | ✅ 实现 | static/slow_zoom/pan 三种运镜，通过 zoompan 和 crop 滤镜 |
| 管线重构 | ✅ 实现 | 视频+音频分离管线，concat demuxer，adelay+atrim 旁白对齐 |
| 代码清理 | ✅ 完成 | 移除无用导入，清理构建产物，统一编码规范 |

### 审计发现

**背景：** 2026-05-25 对代码库与 `docs/lightweight_ai_video_studio_architecture_cn.md` 和 `docs/DEV_PLAN.md` 进行了全面对比审计。

#### 有文档但未实现的功能（10 项 → 6 项待实现）

| # | 功能 | 相关文档 | 计划 |
|---|---|---|---|
| 1 | `xfade` 转场（fade/slide） | DEV_PLAN.md §7.3 | ✅ 已实现 |
| 2 | `loudnorm` 音量归一化 | DEV_PLAN.md §5.2 | ✅ 已实现 |
| 3 | 运镜效果（slow_zoom / pan） | 架构文档 §十一、DEV_PLAN.md 规则 | ✅ 已实现 |
| 4 | 视频+音频分离管线（管线重构） | — | ✅ 已实现 |
| 5 | `FFmpegError` / `AssetNotFoundError` 自定义异常 | DEV_PLAN.md §5.5 | 第三梯队 |
| 6 | 同义词扩展匹配（synonyms.yaml） | DEV_PLAN.md §2.2 | 第三梯队 |
| 7 | Whisper 字幕识别 | 架构文档 §十三 | 第三梯队 |
| 8 | AI 规划层（ai_planner.py） | 架构文档 §十 | ✅ 已实现 — 含主题规划 + 搜索关键词 + 素材下载 |
| 9 | 批量处理（pipeline.py run_batch） | DEV_PLAN.md §9.1 | 第三梯队 |
| 10 | 自动节奏卡点 | 架构文档 §十七 | 未来 |
| 11 | 自动封面生成 | 架构文档 §十七 | 未来 |

#### 部分实现 → 已解决（5 项）

| # | 功能 | 现状 | 计划 |
|---|---|---|---|
| 1 | EXE 图标 | `icon=None` 工作around，`UpdateResourceW` 参数错误（Python 3.14） | 等待上游修复 |
| 2 | `xfade` 转场 | ✅ 已实现并测试 | — |
| 3 | TTS 降级方案 | pyttsx3 已集成，edge-tts → pyttsx3 → silent 自动降级 | ✅ 已实现 |
| 4 | Piper TTS 离线方案 | 架构文档提及但未实现 | 未来 |
| 5 | 性能/压力测试 | DEV_PLAN.md §11.4 有定义但未实现 | 未来 |

#### 已修复的已知问题/缺陷（25 项全修复）

| # | 问题 | 修复 |
|---|---|---|
| 1 | FFmpegBuilder 字典重复 key | 支持 `list[str]` 作为 option 值 |
| 2 | BGM 音量过低（mean -42.5 dB） | `bgm_volume` + `amix:normalize=0` |
| 3 | 无音频流素材导致 BGM 混合失败 | `_has_audio_stream` 探测回退 |
| 4 | 镜头渲染无音频轨道 | `anullsrc` 生成静音音轨（现改为 `-an` 无音频输出） |
| 5 | TTS 缓存返回静音文件 | 文件大小过滤 + volumedetect 静音检测 |
| 6 | ASS 时间格式错误 | `.` 分隔毫秒（原 `,` 冲突） |
| 7 | 音频混合归一化音量减半 | `amix:normalize=0` |
| 8 | 中文系统 tempfile 编码 crash | `encoding="utf-8"` |
| 9 | `os.startfile` 相对路径失败 | `os.path.abspath()` |
| 10 | subprocess WinError 6 (Python 3.14) | `check_ffmpeg` 捕获 `OSError` |
| 11 | 字幕样式全局无法差异化 | 改为 4 元组 `(start, end, text, style)` 逐对话样式 |
| 12 | BGM aloop buffer 硬编码太小 | `aloop=size=2e6` → `size=1000000000`（~6.3 小时） |
| 13 | 单声道 BGM/旁白不兼容 | 添加 `aformat=channel_layouts=stereo:sample_rates=44100` |
| 14 | `check_ffmpeg` 每次调用都检测 | 添加时间戳 TTL 缓存（60s） |
| 15 | 静音检测冗余文件大小判断 | 移除 `st_size < 5000` 启发式规则 |
| 16 | `_global_opts` 类型注解错误 | `dict[str, str]` → `dict[str, str \| list[str]]` |
| 17 | 无意义字符串替换 | `text.replace("\n", "\n")` → 直接 `.split("\n")` |
| 18 | ffprobe 路径推理脆弱 | `ffmpeg_path.replace("ffmpeg", "ffprobe")` → `Path.with_name()` |
| 19 | 占位符缺少 `-map` | 添加显式 `-map 0:v -map 1:a` |
| 20 | 临时 JSON 未清理 | 添加 `_cleanup_temp()` 清理 `_temp_voice` 和 `_temp_subtitle.ass` |
| 21 | concat 路径单引号逃逸 | 添加 `_escape_concat_path()` 函数 |
| 22 | `shutil.copy2` 可能写不完整文件 | 改为 `copy2 → tmp → os.replace()` 原子写 |
| 23 | `has_transitions` 变量赋值顺序错误 | 修正 `concat_with_xfade` 中 `t_type` 顺序 |
| 24 | TTS 速率条件不一致 | 两分支统一使用 `self.speed > 1`（原 `>=`） |
| 25 | 图片时长硬编码 5s | 添加 `-loop -1`（无限循环）支持任意时长 |

### 开发者路线图

#### 第一梯队（MVP 基础功能）✅ 全部完成

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | UTF-8 临时文件编码 | ✅ | script_editor.py 修复 |
| 2 | GUI 缺陷修复 | ✅ | logging import, os.path.abspath |
| 3 | 日志系统增强 | ✅ | sys.excepthook + 三级日志 |
| 4 | BGM 循环缓冲区扩大 | ✅ | size=2e5→2e6 |
| 5 | Voice atrim 防止音频串扰 | ✅ | 添加 atrim=end={duration} |
| 6 | TimelineView+PreviewPanel 集成 | ✅ | 5 个标签页 |
| 7 | script_editor→timeline→preview 信号连接 | ✅ | 完整链路 |
| 8 | 测试覆盖（80+ 新用例） | ✅ | 5 个新测试文件 |

#### 第二梯队（核心体验提升）✅ 全部完成

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | xfade 转场 | ✅ | concat_with_xfade + 滤镜链 |
| 2 | loudnorm 响度归一化 | ✅ | EBU R128 standard |
| 3 | 运镜效果 | ✅ | zoompan + crop 滤镜 |
| 4 | 死代码清理 | ✅ | 移除无用导入、构建产物 |
| 5 | DEV_PLAN.md 更新 | ✅ | 审计结果 + 新路线图 |
| 6 | EXE 图标 | ✅ | 重新生成多分辨率 ICO |

#### 第三轮修复批次（25 项审计 + 管线重构）✅ 全部完成

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | #1-#10 第二轮修复验证 | ✅ | FFmpegBuilder/音量/编码/缓存 |
| 2 | #11-#25 新修复 | ✅ | 字幕4元组/aloop/静音检测/TTL缓存等 |
| 3 | 管线重构 | ✅ | 视频+音频分离，concat demuxer，adelay+atrim |
| 4 | TTS 静音检测重写 | ✅ | ffmpeg volumedetect（替代 ffprobe lavfi） |
| 5 | FFmpeg execute 重写 | ✅ | 线程化管道读取 + cancel_event |
| 6 | QThread 崩溃修复 | ✅ | _worker_cleanup() wait + deleteLater |
| 7 | 编码参数规范化 | ✅ | yuv420p + ar 44100 + timescale 30000 |
| 8 | 168/168 测试通过 | ✅ | 17 个测试文件全覆盖 |
| 9 | 文档全面更新 | ✅ | 7 个文档文件 v0.3.0 |

#### 第三梯队（增强功能）

| # | 任务 | 优先级 | 预计工作量 |
|---|---|---|---|
| 1 | 自定义异常类（FFmpegError, AssetNotFoundError） | 高 | 小 |
| 2 | 同义词扩展匹配 | 高 | 中 |
| 3 | Whisper 字幕识别 | 中 | 大 |
| 4 | AI 规划层（ai_planner.py 集成 + downloader.py） | 中 | 大 | ✅ 已实现 2026-05-27 |
| 5 | Pipeline.run_batch 批量处理 | 高 | 中 |
| 6 | TTS 自动降级（edge-tts→pyttsx3→silent） | 中 | 小 |
| 7 | 性能基准测试 | 低 | 中 |
| 8 | 配置热更新 | 低 | 小 |

### 关键变更记录（相对原始计划）

#### 第三轮修复新增功能

| 功能 | 文件 | 实现方式 |
|---|---|---|
| 管线重构 | `core/renderer.py` `core/pipeline.py` | 视频/音频分离：clip 归一化(-an) → concat demuxer(-f concat) → 旁白(adelay+atrim+amix) → BGM(volume+amix) → loudnorm → mux(-c:v copy -c:a aac) → 字幕叠加 |
| TTS 静音检测 | `core/tts.py` | `ffmpeg -v info -af volumedetect -f null -` 读取 stderr |
| FFmpeg execute 重构 | `core/ffmpeg.py` | 线程化管道读取，cancel_event，超时支持 |
| cancel_event 传播 | `core/pipeline.py` → `core/ffmpeg.py` → `ui/worker.py` | threading.Event 贯穿全链路 |
| QThread 崩溃修复 | `ui/script_editor.py` `ui/batch_panel.py` | _worker_cleanup() wait + deleteLater |
| 编码参数规范化 | `core/renderer.py` `core/ffmpeg.py` | `-pix_fmt yuv420p -ar 44100 -video_track_timescale 30000 -movflags +faststart -g 60 -keyint_min 60` |
| 旁白对齐 | `core/renderer.py` | adelay{ms}:all=1 + atrim=end=duration，替代 concat=n=3:v=0:a=1 |
| BGM 混合简化 | `core/renderer.py` | volume 滤镜 + amix=duration=longest |
| 原子文件写入 | `core/pipeline.py` | copy2 → tmp → os.replace() |
| 临时文件清理 | `core/pipeline.py` | _cleanup_temp() 清理 _temp_voice + _temp_subtitle.ass |

#### AI 增强（第四轮）

| 功能 | 文件 | 实现方式 |
|---|---|---|
| AI 主题规划 | `core/ai_planner.py` | `plan_from_theme()` 通过 LLM 将主题文案转为完整 Script + 搜索关键词，3次重试 |
| 搜索关键词生成 | `core/ai_planner.py` | `suggest_search_queries()` 为已有分段生成英文搜索词 |
| 素材自动下载 | `core/downloader.py` | Pexels/Pixabay API 搜索 + httpx 流式下载 + 自动归档 + 增量扫描 |
| AI 规划对话框 | `ui/ai_plan_dialog.py` | 主题输入 → AI 规划（QThread）→ 预览 → 下载（QThread）→ 保存脚本 |
| 下载器设置 | `ui/settings_dialog.py` | 新增"素材下载"标签页（provider/api_key） |
| 下载器配置 | `config.yaml` / `config.template.yaml` / `config.py` | `downloader.provider/api_key/max_per_query/min_width/timeout` |
| 字幕 4 元组样式 | `core/subtitle.py` `core/renderer.py` | `_format_ass` 逐对话 `(start, end, text, style)` |

#### 第二梯队新增功能（保留）

| 功能 | 文件 | 实现方式 |
|---|---|---|
| xfade 过渡 | `core/ffmpeg.py` concat_with_xfade() | xfade + acrossfade 滤镜链 |
| loudnorm 归一化 | `core/ffmpeg.py` normalize_audio_loudnorm() | EBU R128 (I=-16, TP=-1.5, LRA=11) |
| 运镜效果 | `core/renderer.py` _render_clip_with_asset() | zoompan / crop 滤镜 |
| 多分辨率 ICO | `app.ico` | PIL 生成 16/32/48/256 多尺寸 |

#### 渲染器修复

| 问题 | 修复 |
|---|---|
| FFmpegBuilder 字典重复 key（`map`/`c:v` 等） | 支持 `list[str]` 作为 option 值 |
| BGM 音量过低（mean -42.5 dB） | 使用 `bgm_volume` 做 `volume` 滤镜 + `amix:normalize=0` |
| 无音频流素材导致 BGM 混合失败 | `_has_audio_stream` 探测回退 |
| 镜头片段渲染无音频轨道 | clip 渲染时加入 `anullsrc` 生成静音音轨 |
| TTS 缓存返回静音文件 | 清除旧缓存；`_check_cache` 增加文件大小过滤 |
| 字幕 ASS 时间格式错误 | 改用 `.` 分隔毫秒（原为 `,` 与字段分隔符冲突）|
| 音频混合归一化导致音量减半 | `amix:normalize=0` 取消求和后归一化 |

#### 字幕系统

| 变更 | 说明 |
|---|---|
| 默认使用 **libass 原生字幕滤镜**（通过 `ass=path`）| 质量更高、性能更好 |
| 无 libass 时自动 **回退 Pillow PNG overlay** | 兼容老旧 FFmpeg |
| ASS 文件生成 | `SubtitleGenerator._format_ass()` 使用微软雅黑字体 |
| ASS 路径特殊字符处理 | 冒号 `:` 转义为 `\:`，反斜杠转 `/` |

#### TTS 语音

| 变更 | 说明 |
|---|---|
| 安装 `edge-tts`（在线，微软神经网络语音）| 默认引擎 |
| 安装 `pyttsx3`（离线，Windows SAPI5）| 网络不可用时的回退 |
| 静音回退 `_silent_audio` | 以上均失败时的最终保底 |
| 缓存遍历 | 清除旧静音缓存后重新生成有效音频 |

#### 音频混合（`normalize=0`）

修复前问题：`amix` 默认将各输入求和并除以输入数量（归一化），导致 BGM 和旁白音量被多次减半。

修复后结果：

| 阶段 | 权重 | normalize | 效果 |
|---|---|---|---|
| 旁白混合（voice mix） | 默认 1:1 | `normalize=0` | 旁白与视频音频直接叠加 |
| BGM 混合 | voice=0.7, bgm=0.3 | `normalize=0` | 旁白保持 70%，BGM 30% |

最终参数：`bgm.volume: 0.3`

### 输出规格（sample_knowledge.mp4）

| 项目 | 规格 |
|---|---|
| 时长 | 00:00:21.04 |
| 视频编码 | H.264 (High), 1920×1080, 30fps, 28 kb/s |
| 音频编码 | AAC (LC), 44100 Hz, stereo, 69 kb/s |
| 音量 | mean -26.9 dB, max -3.6 dB（旁白清晰可听） |
| 字幕 | libass 原生硬字幕（直接烧录在画面上） |
| 段落 | 3 段（knowledge / knowledge / fitness），每段 7 秒 |
| BGM | bgm_knowledge.mp3（循环，音量 30%）|

---

## 一、项目概述

### 1.1 项目目标

构建一个可在普通 Windows 电脑上运行的本地优先轻量级 AI 视频创作桌面软件。

**核心理念：** AI 负责规划，程序负责执行。

**系统输入：** 主题文案（AI 规划 → 脚本 JSON）或 脚本 JSON + 本地素材库（图片、视频、音频）

**系统输出：** 自动生成的视频 MP4（含配音、字幕、转场、BGM）

### 1.2 适用视频类型

**推荐：** 知识类、新闻类、口播类、电商类、混剪类、短视频矩阵

**不推荐：** AI 电影、长剧情视频、高级影视特效、AI 原创动画

### 1.3 系统流程

```
  ┌─────────── 输入 A：AI 规划（NEW）───────────┐
  │  主题文案 → AI 生成脚本 → AI 搜索关键词      │
  │      → 自动下载素材 → 分类归档 → 扫描入库    │
  └───────────────┬────────────────────────────┘
                  ↓
  ┌─────────── 输入 B：手动操作 ────────────────┐
  │         脚本 JSON + 本地素材库               │
  └───────────────┬────────────────────────────┘
                  ↓
         素材检索系统（本地标签匹配）
                  ↓
         规则引擎（字幕/转场/运镜规则）
                  ↓
         Timeline 时间轴生成
                  ↓
         音频生成（TTS）
                  ↓
         字幕生成
                  ↓
         FFmpeg 自动渲染
                  ↓
         输出 MP4
```

### 1.4 产品定位

> AI 自动剪辑引擎 — 而不是 AI 视频生成模型

---

## 二、开发环境与依赖

### 2.1 环境要求

| 项目 | 最低要求 | 推荐 |
|---|---|---|
| 操作系统 | Windows 10 | Windows 11 |
| Python | 3.10 | 3.12 |
| 内存 | 8GB | 16GB |
| 硬盘 | SSD 256GB | SSD 512GB |
| GPU | 无要求（可选加速） | RTX 3050+ |
| FFmpeg | 7.0+ | 最新 stable |

### 2.2 Python 依赖

```
# requirements.txt

# GUI 框架
PyQt6>=6.6.0

# TTS 配音（免费，联网）
edge-tts>=6.1.0

# 字幕识别（CPU 可运行）
faster-whisper>=1.0.0

# 数据处理
numpy>=1.24.0

# 数据模型校验
pydantic>=2.5.0
pydantic-settings>=2.1.0

# 配置管理
PyYAML>=6.0.1

# 音频处理
soundfile>=0.12.1

# HTTP 请求（AI 模块）
httpx>=0.25.0
```

### 2.3 外部依赖

| 工具 | 用途 | 安装方式 |
|---|---|---|
| FFmpeg | 视频渲染引擎 | `winget install ffmpeg` 或下载 exe 加入 PATH |
| faster-whisper 模型 | 字幕识别 | 首次启动自动下载（~150MB） |

### 2.4 开发工具建议

| 工具 | 用途 |
|---|---|
| VS Code | 主 IDE |
| Python 插件（ms-python.python） | Python 开发支持 |
| Pylance | 类型检查 |
| pytest | 测试框架 |
| black | 代码格式化 |
| ruff | 代码静态检查 |

---

## 三、项目目录结构

```
ClipForge/
│
├── app.py                        # 主入口，启动 GUI
├── config.yaml                   # 用户配置文件
├── requirements.txt              # Python 依赖清单
│
├── core/                         # 核心逻辑层
│   ├── __init__.py
│   ├── models.py                 # Pydantic 数据模型
│   ├── config.py                 # 配置管理（读取/写入 config.yaml）
│   ├── database.py               # SQLite 数据库管理
│   ├── scanner.py                # 素材扫描器（自动提取元数据+标签）
│   ├── matcher.py                # 关键词素材匹配引擎
│   ├── rules.py                  # 规则引擎（字幕/转场/运镜）
│   ├── timeline.py               # Timeline（时间轴）构建器
│   ├── ai_planner.py             # AI 规划层（可选，默认为空实现）
│   ├── tts.py                    # TTS 配音模块（EdgeTTS + 降级）
│   ├── subtitle.py               # 字幕生成模块（SRT/ASS）
│   ├── ffmpeg.py                 # FFmpeg 命令封装层（Builder 模式）
│   ├── renderer.py               # 渲染编排器（调度 FFmpeg 步骤）
│   └── pipeline.py               # 完整工作流管线（编排所有模块）
│
├── ui/                           # 图形界面层（PyQt6）
│   ├── __init__.py
│   ├── resources.py              # 资源文件（图标、样式表）
│   ├── main_window.py            # 主窗口
│   ├── script_editor.py          # 脚本编辑器（JSON 编辑 + 表单模式）
│   ├── asset_browser.py          # 素材浏览器（表格视图 + 搜索过滤）
│   ├── timeline_view.py          # Timeline 可视化（QGraphicsView）
│   ├── batch_panel.py            # 批量处理面板
│   ├── preview_panel.py          # 预览面板（QMediaPlayer）
│   ├── settings_dialog.py        # 设置对话框
│   └── worker.py                 # 后台任务线程（避免 UI 卡死）
│
├── assets/                       # 用户素材目录（运行时自动扫描）
│   ├── videos/                   # 视频素材
│   ├── images/                   # 图片素材
│   ├── bgm/                      # 背景音乐
│   └── voice/                    # 预设配音（可选）
│
├── scripts/                      # 输入脚本 JSON（默认路径）
├── output/                       # 输出视频
├── cache/                        # 缓存目录
│   ├── tts/                      # TTS 缓存
│   └── subtitle/                 # 字幕缓存
├── database/                     # SQLite 数据库文件
│   └── clipforge.db
│
└── tests/                        # 测试目录
    ├── __init__.py
    ├── conftest.py               # pytest fixtures
    ├── test_models.py
    ├── test_database.py
    ├── test_scanner.py
    ├── test_matcher.py
    ├── test_rules.py
    ├── test_timeline.py
    ├── test_tts.py
    ├── test_subtitle.py
    ├── test_ffmpeg.py
    ├── test_renderer.py
    ├── test_pipeline.py
    └── test_integration.py
```

---

## 四、分阶段开发计划

### Phase 0：项目初始化 ✅ 已完成

**目标：** 搭建项目骨架，确保所有基础依赖可用。

| 编号 | 任务 | 文件 | 验收标准 |
|---|---|---|---|
| 0.1 | 创建 Python 虚拟环境 | `venv/` | `python -m venv venv` 成功 |
| 0.2 | 创建项目目录结构 | 全目录结构 | 所有目录和 `__init__.py` 已创建 |
| 0.3 | 编写 requirements.txt | `requirements.txt` | 执行 `pip install -r requirements.txt` 全部成功 |
| 0.4 | 编写默认配置文件 | `config.yaml` | 包含所有默认配置项，可被 Python 解析 |
| 0.5 | 实现配置管理模块 | `core/config.py` | 可读写 config.yaml，支持配置热更新 |
| 0.6 | 实现 FFmpeg 检测 | `app.py` | 启动时检测 FFmpeg 是否在 PATH，否则弹出提示 |
| 0.7 | 编写入口骨架 | `app.py` | 可空窗口启动，标题栏显示 "ClipForge v0.1" |
| 0.8 | 配置 git 项目 | `.gitignore` | 忽略 venv/, cache/, database/, output/, __pycache__/ |

**config.yaml 默认内容：**

```yaml
# ClipForge 配置文件
app:
  name: ClipForge
  version: 0.2.0

paths:
  assets: ./assets
  scripts: ./scripts
  output: ./output
  cache: ./cache
  database: ./database/clipforge.db

video:
  width: 1920
  height: 1080
  fps: 30
  preset: veryfast
  crf: 23

tts:
  engine: edge-tts          # edge-tts | piper
  voice: zh-CN-XiaoxiaoNeural
  speed: 1.0

subtitle:
  engine: text              # text（脚本直接转）| whisper
  whisper_model: tiny       # tiny | base | small
  device: cpu

ai:
  enabled: false
  provider: openai          # openai | qwen
  api_key: ""
  model: gpt-4o-mini
  max_tokens: 500

bgm:
  volume: 0.3               # BGM 相对音量 0.0~1.0

logging:
  level: INFO               # DEBUG | INFO | WARNING | ERROR
```

---

### Phase 1：数据模型与数据库 ✅ 已完成

**目标：** 定义系统核心数据模型，建立 SQLite 数据库。

#### 任务 1.1：定义 Pydantic 数据模型 — `core/models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class Segment(BaseModel):
    """脚本中的单个分段"""
    id: int
    text: str
    keywords: list[str] = []
    emotion: str = "normal"        # normal | strong | sad | happy | calm
    duration: int = Field(gt=0, le=60, default=5)

class Script(BaseModel):
    """视频脚本"""
    title: str
    duration: int = Field(gt=0, le=3600)
    style: str = "knowledge"       # knowledge | news | entertainment | commerce
    voice: str = "female_01"
    bgm: str = ""
    segments: list[Segment] = Field(min_length=1)

class Asset(BaseModel):
    """本地素材"""
    id: int = 0
    file: str                      # 相对路径（相对于 assets/）
    type: Literal["video", "image", "bgm", "voice"]
    duration: Optional[float] = None
    width: int = 0
    height: int = 0
    tags: list[str] = []
    file_size: int = 0
    created_at: str = ""

class TimelineItem(BaseModel):
    """Timeline 中的一个镜头"""
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    asset: str                     # 素材文件名
    asset_type: str = "video"
    transition: str = "cut"        # cut | fade | slide
    subtitle: str = ""
    subtitle_style: str = "normal" # normal | big_yellow | soft_white | bold
    camera: str = "static"         # static | slow_zoom | pan
    voice_file: Optional[str] = None
    bgm_file: Optional[str] = None

class Timeline(BaseModel):
    """完整时间轴"""
    timeline: list[TimelineItem] = Field(min_length=1)
    output_path: str = ""
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 30
```

#### 任务 1.2：数据库管理 — `core/database.py`

```
功能清单：
  □ 初始化 SQLite 数据库（表结构创建）
  □ 素材 CRUD（增删改查）
  □ 标签搜索（按关键词搜索素材）
  □ 统计查询（素材总数、类型分布）
  □ 数据库文件路径可配置（通过 config.yaml）
```

**数据库表结构：**

```sql
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('video', 'image', 'bgm', 'voice')),
    duration REAL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    tags TEXT DEFAULT '',
    file_size INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_file ON assets(file);

CREATE TABLE IF NOT EXISTS scripts_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
```

#### 任务 1.3：单元测试 — `tests/test_models.py`, `tests/test_database.py`

```
test_models.py:
  □ 验证 Script 模型非法数据拒绝（空 segments、负时长）
  □ 验证 Timeline 模型自动校验
  □ 验证 Asset 模型枚举类型检查

test_database.py:
  □ 初始化数据库表结构
  □ 插入/查询/更新/删除素材
  □ 按标签搜索素材
  □ 搜索不存在的关键词返回空结果
```

---

### Phase 2：素材扫描与匹配引擎 ✅ 已完成

**目标：** 实现素材自动扫描入库和关键词匹配。

#### 任务 2.1：素材扫描器 — `core/scanner.py`

**扫描逻辑：**

```
1. 遍历 assets/ 下所有子目录
2. 对于每个文件：
   a. 检查是否已存在于数据库（by 文件名+修改时间）
   b. 如已存在且未修改 → 跳过
   c. 如新增或已修改 → 提取元数据
3. 元数据提取：
   - 视频：用 ffprobe 提取时长、分辨率
   - 图片：提取尺寸（可选，依赖 PIL）
   - 音频：用 ffprobe 提取时长
   - 标签：从文件名和所在目录名称自动提取关键词
4. 写入 SQLite 数据库
```

**标签提取规则（从文件名自动推断）：**

```python
def extract_tags_from_path(file_path: str) -> list[str]:
    """
    从文件路径提取标签：
    - 文件名（不含扩展名）按分隔符拆分：-, _, 空格
    - 父目录名作为额外标签
    - 过滤常见停用词
    """
    # 示例: assets/videos/food/healthy_salad.mp4
    # → tags: ["healthy", "salad", "food"]
```

**Scanner API：**

```python
class AssetScanner:
    def scan_all(self) -> int: ...          # 全量扫描，返回新增数
    def scan_incremental(self) -> int: ...  # 增量扫描（仅新/修改文件）
    def remove_deleted(self) -> int: ...    # 删除数据库中已不存在的记录
```

#### 任务 2.2：素材匹配引擎 — `core/matcher.py`

**匹配算法（三种模式）：**

```python
class Matcher:
    def __init__(self, strategy: str = "keyword"):
        self.strategy = strategy  # keyword | synonym | hybrid

    def match(
        self,
        text: str,
        keywords: list[str],
        top_k: int = 3,
        asset_type: str = "video"
    ) -> list[Asset]:
        """
        匹配逻辑：
        1. keyword 模式：关键词直接匹配标签（交集匹配）
        2. synonym 模式：关键词 + 同义词表扩展匹配
        3. hybrid 模式：keyword + text 全文关键词提取后匹配

        返回按匹配度排序的 TopK 素材列表
        """
```

**同义词文件（`config/synonyms.yaml`，可选）：**

```yaml
# 同义词映射表
synonyms:
  减脂: [减肥, 瘦身, 燃脂, 减重]
  健身: [运动, 锻炼, 训练,  workout]
  饮食: [食物, 餐饮, 膳食, 营养]
  跑步: [慢跑, jogging, 奔跑]
```

**匹配度评分算法：**

```python
def score(self, asset: Asset, keywords: list[str], synonyms: dict) -> float:
    matched = 0
    asset_tags = set(t.lower() for t in asset.tags)
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in asset_tags:
            matched += 2.0  # 精确匹配权重高
        elif kw_lower in synonyms:
            for syn in synonyms[kw_lower]:
                if syn.lower() in asset_tags:
                    matched += 1.0  # 同义词匹配权重较低
    return matched / len(keywords) if keywords else 0
```

#### 任务 2.3：单元测试 — `tests/test_scanner.py`, `tests/test_matcher.py`

```
test_scanner.py:
  □ 扫描空目录返回 0
  □ 扫描含视频文件的目录返回正确数量
  □ 重复扫描不重复插入
  □ 标签从文件名和目录正确提取

test_matcher.py:
  □ 关键词精确匹配返回正确素材
  □ 关键词部分匹配返回按匹配度排序的结果
  □ 无匹配关键词返回空列表
  □ TopK 参数生效
  □ 同义词扩展匹配生效
```

---

### Phase 3：规则引擎 ✅ 已完成

**目标：** 实现可扩展的规则引擎，用规则替代大部分 AI 推理。

#### 任务 3.1：规则引擎核心 — `core/rules.py`

**规则定义结构：**

```python
from typing import Protocol, Any

class Rule(Protocol):
    name: str
    priority: int              # 数字越大越优先

    def apply(self, context: dict) -> dict:
        """输入 context，输出规则决策结果"""
        ...

class RuleEngine:
    def __init__(self):
        self.rules: list[Rule] = []

    def register(self, rule: Rule):
        """注册规则（按 priority 排序）"""
        ...

    def execute(self, context: dict) -> dict:
        """按优先级执行所有规则，结果合并"""
        ...
```

#### 任务 3.2：内置规则实现

```python
# ----- 字幕样式规则 -----
class SubtitleStyleRule(Rule):
    name = "subtitle_style"
    priority = 10

    def apply(self, ctx):
        emotion = ctx.get("emotion", "normal")
        style_map = {
            "strong":  {"style": "big_yellow", "font_size": 48, "color": "#FFD700"},
            "sad":     {"style": "soft_white", "font_size": 36, "color": "#FFFFFF"},
            "happy":   {"style": "bold",       "font_size": 42, "color": "#FF6B6B"},
            "calm":    {"style": "soft_white", "font_size": 36, "color": "#E0E0E0"},
            "normal":  {"style": "normal",     "font_size": 36, "color": "#FFFFFF"},
        }
        return {"subtitle": style_map.get(emotion, style_map["normal"])}

# ----- 转场规则 -----
class TransitionRule(Rule):
    name = "transition"
    priority = 8

    def apply(self, ctx):
        duration = ctx.get("duration", 5)
        if duration <= 3:
            return {"transition": "cut"}
        elif duration <= 8:
            return {"transition": "fade"}
        else:
            return {"transition": "slide"}

# ----- 运镜规则 -----
class CameraRule(Rule):
    name = "camera"
    priority = 6

    def apply(self, ctx):
        style = ctx.get("style", "knowledge")
        camera_map = {
            "knowledge":     "slow_zoom",
            "news":          "static",
            "entertainment": "pan",
            "commerce":      "slow_zoom",
        }
        return {"camera": camera_map.get(style, "static")}

# ----- BGM 规则 -----
class BGMRule(Rule):
    name = "bgm"
    priority = 5

    def apply(self, ctx):
        style = ctx.get("style", "knowledge")
        bgm_map = {
            "knowledge":     "bgm_knowledge.mp3",
            "news":          "bgm_news.mp3",
            "entertainment": "bgm_upbeat.mp3",
            "commerce":      "bgm_commerce.mp3",
        }
        bgm = bgm_map.get(style, "")
        return {"bgm": bgm} if bgm else {}
```

#### 任务 3.3：单元测试 — `tests/test_rules.py`

```
  □ 规则引擎正确注册和执行规则
  □ 字幕样式 rule：emotion=strong → big_yellow
  □ 转场 rule：duration=2 → cut，duration=5 → fade
  □ 运镜 rule：style=news → static
  □ 多条规则结果正确合并
  □ 规则优先级生效
```

---

### Phase 4：Timeline 构建系统 ✅ 已完成

**目标：** 实现从脚本到 Timeline 的自动构建。

#### 任务 4.1：Timeline 构建器 — `core/timeline.py`

```python
class TimelineBuilder:
    def __init__(self, matcher: Matcher, rule_engine: RuleEngine):
        self.matcher = matcher
        self.rules = rule_engine

    def build(self, script: Script) -> Timeline:
        """
        构建流程：
        1. 对每个 segment，调用 matcher 匹配素材
        2. 对每个 segment，调用 rule_engine 应用规则
        3. 组装 TimelineItem
        4. 计算时间偏移（累计 start/end）
        5. 返回完整 Timeline
        """
        items: list[TimelineItem] = []
        current_time = 0.0

        for segment in script.segments:
            # 匹配素材
            assets = self.matcher.match(
                text=segment.text,
                keywords=segment.keywords,
                top_k=1
            )
            matched_asset = assets[0] if assets else None

            # 应用规则
            rule_ctx = {
                "emotion": segment.emotion,
                "duration": segment.duration,
                "style": script.style,
            }
            rule_result = self.rules.execute(rule_ctx)

            # 构建 TimelineItem
            item = TimelineItem(
                start=current_time,
                end=current_time + segment.duration,
                asset=matched_asset.file if matched_asset else "",
                asset_type=matched_asset.type if matched_asset else "video",
                transition=rule_result.get("transition", "cut"),
                subtitle=segment.text,
                subtitle_style=rule_result.get("subtitle", {}).get("style", "normal"),
                camera=rule_result.get("camera", "static"),
            )
            items.append(item)
            current_time += segment.duration

        return Timeline(
            timeline=items,
            resolution=(1920, 1080),
            fps=30,
        )
```

#### 任务 4.2：Timeline 校验器

```python
class TimelineValidator:
    def validate(self, timeline: Timeline) -> list[str]:
        """
        检查：
        - 时间不重叠
        - 所有素材文件存在
        - 素材类型正确
        - 时长非负
        - 分辨率合法
        返回错误信息列表，空列表表示通过
        """
```

#### 任务 4.3：单元测试 — `tests/test_timeline.py`

```
  □ 有效脚本生成有效 Timeline
  □ Timeline 时间连续性正确（不重叠、无间隙）
  □ 无匹配素材时返回空 asset 字段（不崩溃）
  □ 校验器检测到时间冲突
  □ 校验器检测到素材文件不存在
  □ 校验器通过有效 Timeline
```

---

### Phase 5：TTS 配音模块 ✅ 已完成

**目标：** 实现文本转语音，支持联网和离线模式。

#### 任务 5.1：EdgeTTS 集成 — `core/tts.py`

```python
import asyncio
import edge_tts
from pathlib import Path

class TTSModule:
    def __init__(self, config: dict):
        self.engine = config.get("engine", "edge-tts")
        self.voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.speed = config.get("speed", 1.0)
        self.cache_dir = Path(config.get("cache_dir", "./cache/tts"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def _edge_tts(self, text: str, output_path: str):
        """EdgeTTS 异步生成"""
        communicate = edge_tts.Communicate(text, self.voice, rate=f"+{int((self.speed-1)*50)}%")
        await communicate.save(output_path)

    def generate(self, text: str, output_path: str) -> str:
        """
        生成配音：
        1. 检查缓存（文本 hash）
        2. 缓存命中 → 直接返回
        3. 缓存未命中 → 调用 TTS 生成 → 缓存 → 返回
        4. 失败时尝试降级方案
        """
        ...

    def generate_batch(self, segments: list[tuple[int, str]], output_dir: str) -> list[str]:
        """批量生成，返回配音文件路径列表"""
        ...
```

#### 任务 5.2：音频归一化

```python
def normalize_audio(input_path: str, output_path: str):
    """调用 FFmpeg loudnorm filter 归一化音量"""
    # ffmpeg -i input.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 output.wav
    ...
```

#### 任务 5.3：降级方案

```python
class FallbackTTS:
    """
    当 EdgeTTS 不可用（无网络）时的降级方案：
    - 使用 Python 内置的 pyttsx3（基于 SAPI5）
    - 效果略差但完全离线
    """
    def generate(self, text: str, output_path: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
```

#### 任务 5.4：单元测试 — `tests/test_tts.py`

```
  □ TTS 生成 wav 文件存在且非空
  □ 缓存机制：相同文本第二次调用不重复生成
  □ 音频归一化后音量达标
  □ 批量生成返回正确数量的文件列表
```

---

### Phase 6：字幕模块 ✅ 已完成

**目标：** 实现字幕生成，支持文本直接转字幕和 Whisper 识别两种模式。

#### 任务 6.1：文本模式字幕 — `core/subtitle.py`

```python
class SubtitleGenerator:
    def __init__(self, config: dict):
        self.mode = config.get("engine", "text")
        self.whisper_model = config.get("whisper_model", "tiny")
        self.device = config.get("device", "cpu")

    def generate_from_text(
        self,
        segments: list[tuple[float, float, str]],
        output_path: str,
        style: str = "normal"
    ) -> str:
        """
        从脚本文本直接生成字幕（模式A）
        输入: [(start_time, end_time, text), ...]
        输出: SRT/ASS 文件路径
        """
        ...

    def generate_from_audio(
        self,
        audio_path: str,
        script_segments: list[tuple[int, str]],
        output_path: str,
        style: str = "normal"
    ) -> str:
        """
        从配音音频识别生成字幕（模式B）
        使用 faster-whisper 识别，然后对齐到脚本分段
        """
        ...
```

#### 任务 6.2：SRT 格式生成

```python
def format_srt(segments: list[tuple[float, float, str]]) -> str:
    """
    1
    00:00:01,000 --> 00:00:05,000
    减脂核心是饮食

    2
    00:00:05,000 --> 00:00:11,000
    不是运动不够，而是饮食错误
    """
    ...
```

#### 任务 6.3：ASS 格式生成（带样式）

```python
def format_ass(
    segments: list[tuple[float, float, str]],
    style: str = "normal"
) -> str:
    """
    ASS 格式支持字体、颜色、位置等样式：
    - normal: 白色，底部居中，字体大小 36
    - big_yellow: 黄色，底部居中，字体大小 48，加粗
    - soft_white: 白色半透明，底部居中，字体大小 36
    - bold: 白色，底部居中，字体大小 42，加粗
    """
    ...
```

#### 任务 6.4：单元测试 — `tests/test_subtitle.py`

```
  □ SRT 格式符合规范
  □ ASS 格式包含样式定义
  □ 不同 style 参数产生不同的 ASS 样式
  □ 空 segments 列表返回空字幕文件
  □ 时间格式正确（毫秒对齐）
```

---

### Phase 7：FFmpeg 渲染引擎 ✅ 已完成

**目标：** 实现完整的 FFmpeg 渲染管线。

#### 任务 7.1：FFmpeg 命令封装 — `core/ffmpeg.py`

```python
class FFmpegBuilder:
    """
    FFmpeg 命令链式构建器

    用法:
        cmd = (FFmpegBuilder()
            .input("video.mp4")
            .input("subtitle.ass")
            .filter_complex("[0:v]subtitles=subtitle.ass[v]")
            .output("output.mp4", {"c:v": "libx264", "preset": "veryfast"})
            .build())
    """
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self.inputs: list[str] = []
        self.outputs: list[str] = []
        ...

    def input(self, path: str, options: dict = None) -> "FFmpegBuilder": ...
    def filter_complex(self, filter_str: str) -> "FFmpegBuilder": ...
    def output(self, path: str, codec: dict = None) -> "FFmpegBuilder": ...
    def overwrite(self) -> "FFmpegBuilder": ...
    def build(self) -> list[str]: ...  # 返回完整的命令行参数列表
```

#### 任务 7.2：视频拼接

```python
def concat_videos(
    input_files: list[str],
    output_path: str,
    transitions: list[str],
    resolution: tuple[int, int] = (1920, 1080)
):
    """
    视频拼接策略（推荐分段渲染后拼接）：

    方案：每个镜头单独渲染 → FFmpeg concat demuxer 合并

    步骤：
    1. 对每个 TimelineItem 渲染为独立临时文件
       - 如有转场，前一个镜头预留 overlap 帧
       - 叠加字幕和水印
    2. 生成 concat 文件列表
    3. FFmpeg concat 合并
    4. 清理临时文件
    """
    ...
```

#### 任务 7.3：转场效果

```python
def apply_transition(
    clip_a: str,
    clip_b: str,
    transition: str,
    duration: float,
    output_path: str
):
    """
    支持的转场：
    - cut: 直接拼接（无转场）
    - fade: 交叉淡入淡出（ffmpeg xfade filter）
    - slide: 滑动（简单实现，用 xfade=slideleft）
    """
    # cut: concat 直接拼接
    # fade: xfade=transition=fade:duration=0.5:offset=...
    # slide: xfade=transition=slideleft:duration=0.5:offset=...
```

#### 任务 7.4：字幕叠加

```python
def overlay_subtitle(
    video_path: str,
    subtitle_path: str,
    output_path: str
):
    """使用 subtitles filter 叠加 ASS/SRT 字幕"""
    # ffmpeg -i video.mp4 -vf "subtitles=subtitle.ass" output.mp4
```

#### 任务 7.5：音频混合

```python
def mix_audio(
    video_path: str,
    voice_path: str,
    bgm_path: Optional[str],
    bgm_volume: float = 0.3,
    output_path: str
):
    """
    混音：
    1. 配音主音量
    2. BGM 降低音量后混合
    3. BGM 自动循环/淡出
    """
    # ffmpeg -i video.mp4 -i voice.wav -i bgm.mp3 \
    #   -filter_complex "[1:a]volume=1.0[a1];[2:a]volume=0.3,aloop=loop=-1:size=2e5[a2];[a1][a2]amix=inputs=2:duration=first" \
    #   -c:v copy output.mp4
```

#### 任务 7.6：渲染进度回调

```python
def execute_with_progress(
    cmd: list[str],
    progress_callback: callable = None,
    total_duration: float = None
):
    """
    执行 FFmpeg 命令并解析进度
    解析 stderr 中的 time=HH:MM:SS.MS 计算百分比
    通过 progress_callback(percent) 回调
    """
    ...
```

#### 任务 7.7：单元测试 — `tests/test_ffmpeg.py`

```
  □ FFmpegBuilder 生成正确的命令行参数
  □ 带输入文件的命令格式正确
  □ 带 filter_complex 的命令格式正确
  □ 检查 FFmpeg 是否可用（环境检测）
  □ 进度解析函数正确提取 time 值
```

---

### Phase 8：渲染编排器 ✅ 已完成

**目标：** 整合 FFmpeg 各功能，根据 Timeline 完成渲染。

#### 任务 8.1：渲染编排器 — `core/renderer.py`

```python
class Renderer:
    def __init__(self, config: dict):
        self.resolution = (config["video"]["width"], config["video"]["height"])
        self.fps = config["video"]["fps"]
        self.preset = config["video"]["preset"]
        self.crf = config["video"]["crf"]
        self.temp_dir = Path("./cache/render_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def render(self, timeline: Timeline, progress_callback=None) -> str:
        """
        完整渲染流程：
        1. 创建临时工作目录
        2. 逐镜头渲染（含转场）
        3. 合并所有镜头
        4. 叠加字幕
        5. 混合配音（如有）
        6. 混合 BGM（如有）
        7. 输出最终视频
        8. 清理临时文件
        """
        ...

    def _render_clip(self, item: TimelineItem, index: int, output_path: str):
        """渲染单个镜头"""
        ...

    def _concat_clips(self, clip_files: list[str], output_path: str):
        """合并所有镜头"""
        ...
```

#### 任务 8.2：单元测试 — `tests/test_renderer.py`

```
  □ 渲染单个镜头输出文件存在
  □ 完整 Timeline 渲染输出 MP4 可播放
  □ 不同转场效果正确应用
  □ 字幕叠加正确
  □ 音频混合正确
```

---

### Phase 9：Pipeline 工作流管线 ✅ 已完成

**目标：** 编排所有模块，实现一键式视频生成。

#### 任务 9.1：Pipeline 编排器 — `core/pipeline.py`

```python
from enum import Enum
from dataclasses import dataclass

class PipelineStep(Enum):
    LOAD_SCRIPT = "load_script"
    MATCH_ASSETS = "match_assets"
    APPLY_RULES = "apply_rules"
    BUILD_TIMELINE = "build_timeline"
    GENERATE_TTS = "generate_tts"
    GENERATE_SUBTITLE = "generate_subtitle"
    RENDER_VIDEO = "render_video"

@dataclass
class PipelineProgress:
    step: PipelineStep
    progress: float    # 0.0 ~ 1.0
    message: str

class Pipeline:
    def __init__(self, config: dict):
        self.config = config
        self.matcher = Matcher()
        self.rules = RuleEngine()
        self.timeline_builder = TimelineBuilder(self.matcher, self.rules)
        self.tts = TTSModule(config)
        self.subtitle = SubtitleGenerator(config)
        self.renderer = Renderer(config)

    def run(
        self,
        script_path: str,
        output_path: str,
        progress_callback: callable = None
    ) -> str:
        """
        完整工作流：
        1. 读取脚本 JSON
        2. 素材匹配（每个 segment）
        3. 规则引擎决策
        4. 构建 Timeline
        5. 生成 TTS 配音
        6. 生成字幕
        7. FFmpeg 渲染
        8. 返回输出路径
        """
        ...

    def run_batch(
        self,
        script_paths: list[str],
        output_dir: str,
        progress_callback: callable = None
    ) -> list[str]:
        """批量处理多个脚本"""
        ...

    def validate_script(self, script_path: str) -> list[str]:
        """验证脚本 JSON 合法性"""
        ...
```

**详细 Pipeline 流程：**

```python
def run(self, script_path: str, output_path: str, progress_callback=None):
    # Step 1: 加载脚本
    self._report(progress_callback, PipelineStep.LOAD_SCRIPT, 0.0, "加载脚本...")
    script = self._load_script(script_path)

    # Step 2: 素材匹配
    self._report(progress_callback, PipelineStep.MATCH_ASSETS, 0.0, "匹配素材...")
    matched_assets = {}
    for i, seg in enumerate(script.segments):
        assets = self.matcher.match(seg.text, seg.keywords)
        matched_assets[seg.id] = assets
        self._report(progress_callback, PipelineStep.MATCH_ASSETS,
                     (i + 1) / len(script.segments), f"匹配素材 {i+1}/{len(script.segments)}")

    # Step 3: 规则引擎
    self._report(progress_callback, PipelineStep.APPLY_RULES, 0.5, "应用规则...")

    # Step 4: 构建 Timeline
    self._report(progress_callback, PipelineStep.BUILD_TIMELINE, 0.0, "构建时间轴...")
    timeline = self.timeline_builder.build(script)

    # Step 5: TTS 配音
    self._report(progress_callback, PipelineStep.GENERATE_TTS, 0.0, "生成配音...")
    voice_dir = Path(output_path).parent / "temp_voice"
    voice_files = self.tts.generate_batch(
        [(seg.id, seg.text) for seg in script.segments],
        str(voice_dir)
    )
    # 将配音文件关联到 Timeline
    for item, vf in zip(timeline.timeline, voice_files):
        item.voice_file = vf

    # Step 6: 字幕生成
    self._report(progress_callback, PipelineStep.GENERATE_SUBTITLE, 0.0, "生成字幕...")
    subtitle_path = str(Path(output_path).parent / "temp_subtitle.ass")
    subtitle_segments = []
    for item in timeline.timeline:
        subtitle_segments.append((item.start, item.end, item.subtitle))
    self.subtitle.generate_from_text(subtitle_segments, subtitle_path)

    # Step 7: 渲染
    self._report(progress_callback, PipelineStep.RENDER_VIDEO, 0.0, "渲染视频...")
    timeline.output_path = output_path
    result = self.renderer.render(timeline, progress_callback=lambda p: None)

    # 清理临时文件
    shutil.rmtree(voice_dir, ignore_errors=True)
    Path(subtitle_path).unlink(missing_ok=True)

    return result
```

#### 任务 9.2：单元测试 — `tests/test_pipeline.py`

```
  □ 完整管线执行成功输出 MP4
  □ 脚本 JSON 格式错误时正确报告
  □ 素材不存在时自动跳过（不崩溃）
  □ 批量处理正确返回所有结果路径
  □ 进度回调被正确调用
```

---

### Phase 10：PyQt6 GUI 完整版 ✅ 已完成

**目标：** 构建完整的 Windows 桌面界面。

#### 任务 10.1：主窗口框架 — `ui/main_window.py`

```python
class MainWindow(QMainWindow):
    """
    主窗口结构：
    ┌─────────────────────────────────────────────┐
    │ 菜单: [文件] [编辑] [工具] [帮助]             │
    ├─────────────────────────────────────────────┤
    │ Tab 栏: [脚本编辑] [素材管理] [批量处理] [设置] │
    ├─────────────────────────────────────────────┤
    │                                             │
    │          中央内容区（按 Tab 切换）              │
    │                                             │
    ├─────────────────────────────────────────────┤
    │ 状态栏: 素材数: 120 | 就绪                    │
    └─────────────────────────────────────────────┘
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClipForge - AI 视频剪辑引擎")
        self.setMinimumSize(1280, 800)
        self._setup_menu()
        self._setup_tabs()
        self._setup_status_bar()

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导入脚本...", self._import_script)
        file_menu.addAction("导入素材...", self._import_assets)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("偏好设置...", self._open_settings)

        tool_menu = menubar.addMenu("工具(&T)")
        tool_menu.addAction("扫描素材库", self._scan_assets)
        tool_menu.addSeparator()
        tool_menu.addAction("生成视频", self._generate_video, QKeySequence("Ctrl+R"))

        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于 ClipForge", self._show_about)

    def _setup_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(ScriptEditorTab(), "脚本编辑")
        self.tabs.addTab(AssetBrowserTab(), "素材管理")
        self.tabs.addTab(BatchPanelTab(), "批量处理")
        self.tabs.addTab(SettingsTab(), "设置")
        self.setCentralWidget(self.tabs)

    def _setup_status_bar(self):
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label, 1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
```

#### 任务 10.2：脚本编辑器 — `ui/script_editor.py`

```
功能：
  □ JSON 文本编辑器（带语法高亮和验证）
  □ 表单模式（表格式分段编辑）
  □ 新建/打开/保存脚本
  □ 脚本格式验证（实时提示错误位置）
  □ 一键生成视频按钮
  □ 预览 Timeline 按钮

布局：
  +------------------------------------------+
  | [新建] [打开] [保存] [验证] | [▶ 生成] [预览] |
  +------------------------------------------+
  | [JSON 模式] [表单模式]  ← 双模式切换       |
  +------------------------------------------+
  |  JSON 编辑器区域          |  分段参数面板   |
  |  (QPlainTextEdit)        |  ID | 文本 |... |
  |                          |  [添加分段]     |
  +------------------------------------------+
```

#### 任务 10.3：素材浏览器 — `ui/asset_browser.py`

```
功能：
  □ 表格显示所有素材（文件名、类型、时长、标签、分辨率）
  □ 搜索过滤（按关键词搜索）
  □ 类型过滤下拉框（全部/视频/图片/BGM/配音）
  □ 双击预览素材
  □ 标签编辑（双击标签单元格编辑）
  □ 扫描素材库按钮
  □ 拖拽导入新素材

布局：
  +------------------------------------------+
  | [扫描素材库] [导入素材]                    |
  | 搜索: [___________]  类型: [全部 ▼]       |
  +------------------------------------------+
  |  表格视图 (QTableView)                    |
  |  ID | 文件名 | 类型 | 时长 | 标签 | 尺寸  |
  |  ...                                      |
  +------------------------------------------+
  | 状态: 共 N 个素材                           |
  +------------------------------------------+
```

#### 任务 10.4：Timeline 可视化 — `ui/timeline_view.py`

```python
class TimelineView(QGraphicsView):
    """
    基于 QGraphicsScene 的 Timeline 可视化
    - 每个镜头为彩色矩形块
    - 颜色按 emotion 区分（normal=蓝, strong=红, happy=绿）
    - 鼠标悬停显示镜头信息
    - 支持拖拽调整镜头顺序
    - 支持拖拽调整时长
    - 支持播放预览（配合 QMediaPlayer）
    """
```

#### 任务 10.5：批量处理面板 — `ui/batch_panel.py`

```
功能：
  □ 拖拽/添加多个脚本文件
  □ 显示处理队列
  □ 批量生成（串行处理）
  □ 总体进度显示（当前文件/总数）
  □ 每个文件的单独进度
  □ 处理结果（成功/失败）
  □ 一键打开输出目录

布局：
  +------------------------------------------+
  | [添加脚本] [清空列表] 输出目录: [...]      |
  +------------------------------------------+
  |  文件列表 (QListWidget)                    |
  |  □ script_01.json    [▶ 待处理]           |
  |  □ script_02.json    [✓ 已完成]           |
  |  □ script_03.json    [✗ 失败: 素材不足]   |
  +------------------------------------------+
  |  总体进度: [████████░░░░] 2/3             |
  |  [▶ 开始批量处理] [打开输出目录]           |
  +------------------------------------------+
```

#### 任务 10.6：设置对话框 — `ui/settings_dialog.py`

```python
class SettingsDialog(QDialog):
    """
    设置选项：
    通用
    ├── 素材目录: [___________] [浏览...]
    ├── 输出目录: [___________] [浏览...]
    ├── 默认分辨率: [1920x1080 ▼]
    └── 默认 FPS: [30 ▼]

    配音
    ├── TTS 引擎: [edge-tts ▼]
    ├── 语音: [zh-CN-XiaoxiaoNeural ▼]
    └── 语速: [1.0] (滑块)

    字幕
    ├── 模式: [文本 ▼] (文本/Whisper)
    └── Whisper 模型: [tiny ▼]

    AI（可选）
    ├── 启用 AI 规划: [☐]
    ├── API 提供商: [openai ▼]
    ├── API Key: [____________]
    └── 模型: [gpt-4o-mini ▼]

    渲染
    ├── 编码预设: [veryfast ▼]
    └── CRF: [23]

    [恢复默认] [取消] [保存]
    """
```

#### 任务 10.7：后台工作线程 — `ui/worker.py`

```python
class PipelineWorker(QThread):
    """
    后台执行 Pipeline，避免 UI 卡死

    信号:
        progress_updated(PipelineProgress)  # 进度更新
        step_changed(str)                   # 当前步骤描述
        finished(str)                       # 完成，返回输出路径
        error(str)                          # 出错，返回错误信息

    用法:
        worker = PipelineWorker(config, script_path, output_path)
        worker.progress_updated.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)
        worker.start()
    """
    progress_updated = Signal(PipelineProgress)
    step_changed = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, config, script_path, output_path):
        super().__init__()
        self.config = config
        self.script_path = script_path
        self.output_path = output_path
        self._cancelled = False

    def run(self):
        pipeline = Pipeline(self.config)
        try:
            result = pipeline.run(
                self.script_path,
                self.output_path,
                progress_callback=self._on_progress
            )
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True

    def _on_progress(self, progress: PipelineProgress):
        self.progress_updated.emit(progress)
```

#### 任务 10.8：预览面板 — `ui/preview_panel.py`

```python
class PreviewPanel(QWidget):
    """
    视频预览面板：
    - 使用 QMediaPlayer + QVideoWidget
    - 播放/暂停/停止控制
    - 进度条拖拽
    - 音量控制
    - 全屏切换
    """
    def __init__(self):
        self.player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        self.play_btn = QPushButton("▶")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.time_label = QLabel("00:00 / 00:00")
```

#### 任务 10.9：GUI 集成测试

```
手动测试清单：
  □ 主窗口无报错启动，标题正确
  □ 所有 Tab 页可切换
  □ 脚本编辑器：可新建/打开/保存/验证 JSON
  □ 素材浏览器：表格显示、搜索过滤、标签编辑
  □ Timeline 预览：色块显示正确
  □ 生成视频：进度条更新，完成后提示
  □ 批量处理：多脚本逐一完成
  □ 设置：修改配置后生效并持久化
  □ 错误处理：FFmpeg 未安装时有提示
  □ 窗口缩放：布局自适应
```

---

### Phase 11：测试全面覆盖 ✅ 已完成（168/168 测试通过）

#### 11.1 单元测试（pytest）

每个核心模块的单元测试覆盖率目标 > 80%。

```bash
# 运行所有单元测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_matcher.py -v

# 带覆盖率报告
pytest tests/ --cov=core --cov-report=html
```

#### 11.2 集成测试 — `tests/test_integration.py`

```python
"""
集成测试场景：

1. 素材管理集成测试
   - 扫描测试素材 → 数据库验证
   - 关键词匹配 → 结果验证

2. 规则 + Timeline 集成测试
   - 输入脚本 → 规则引擎 → Timeline 构建
   - 验证 Timeline 结构完整

3. 完整管线集成测试
   - 使用测试脚本 → Pipeline 运行
   - 验证输出 MP4 存在且可播放
   - 验证配音轨道存在
   - 验证字幕正确叠加
"""
```

#### 11.3 E2E 测试

```python
"""
端到端测试（需有测试素材）：

test_e2e_short:
  - 脚本：2 segments, 10 秒总时长
  - 验证：输出存在，时长误差 < 1s，配音可闻，字幕可见

test_e2e_normal:
  - 脚本：5 segments, 30 秒总时长
  - 验证：同上 + 转场效果 + BGM

test_e2e_batch:
  - 3 个测试脚本批量处理
  - 验证：全部成功输出
"""
```

#### 11.4 性能测试

```python
"""
性能基准：

1. 素材扫描：100 文件 → < 5 秒
2. Timeline 构建：10 segments → < 1 秒
3. TTS 生成：100 字 → < 3 秒
4. 视频渲染：1 分钟视频 → < 10 分钟（不含 TTS/字幕）
5. 内存峰值：< 2GB（含 Whisper 模型）
6. 批量处理：10 个 30 秒脚本 → < 60 分钟
"""
```

---

### Phase 12：打包与发布 ✅ 已完成（含 BUILD.bat + clipforge.spec）

**目标：** 打包为 Windows 可安装的桌面应用。

#### 12.1 打包工具

```bash
# 使用 PyInstaller 打包为单个 exe
pip install pyinstaller

pyinstaller --onefile --windowed --name "ClipForge" `
    --add-data "config.yaml;." `
    --add-data "core;core" `
    --add-data "ui;ui" `
    --icon app.ico `
    app.py
```

#### 12.2 安装包制作

```bash
# 使用 NSIS 或 Inno Setup 制作安装包
# 包含：
# - 主程序 exe
# - 默认配置文件
# - 示例脚本
# - 快捷方式
# - FFmpeg 检测/安装引导
```

#### 12.3 发布清单

```
ClipForge_v1.0.0_Setup.exe
├── app.exe (PyInstaller 打包)
├── config.yaml
├── scripts/
│   ├── sample_knowledge.json
│   └── sample_commerce.json
└── README.txt
```

---

## 五、关键模块设计决策

### 5.1 渲染策略

**推荐方案：分段渲染 + FFmpeg concat**

```
1. 每个 TimelineItem 单独渲染为临时 MP4
   - 用 FFmpeg 创建纯色/图片背景 + 素材叠加
   - 字幕直接渲染进视频
2. 使用 FFmpeg concat demuxer 合并
3. 叠加配音 + BGM（amix filter）
4. 清理临时文件
```

**优点：** 实现简单、错误隔离好、每段可独立调试
**缺点：** 中间文件占磁盘（可配置清理）
**替代方案：** 单次 FFmpeg filter_complex（更复杂但无中间文件，作为后续优化方向）

### 5.2 AI 集成方案

```
AI 模块设计原则：默认关闭，按需启用。

启用后 AI 负责：
  1. 素材选择：从 TopK 素材中推荐最佳匹配
  2. 文案优化：优化口播文案的可读性
  3. 节奏规划：建议镜头时长和切换节奏

AI 不负责：
  × 生成视频
  × 理解视频/图片内容
  × 全自动创作

配置控制（config.yaml）：
  ai.enabled: false        # 默认关闭
  ai.provider: openai      # openai | qwen | deepseek
  ai.api_key: ""           # 用户自行填入
  ai.model: gpt-4o-mini    # 低成本模型
```

### 5.3 并发与多线程策略

| 场景 | 策略 | 说明 |
|---|---|---|
| GUI 操作 | 主线程 | 响应式 UI |
| 渲染管线 | QThread | 后台运行，信号通信 |
| TTS 批量生成 | asyncio + 线程池 | EdgeTTS 原生异步 |
| 批量视频生成 | 串行或最多 2 并发 | 避免资源耗尽 |
| 素材扫描 | QThread | 大目录扫描不卡 UI |

### 5.4 缓存策略

| 缓存类型 | 位置 | Key | 有效期 |
|---|---|---|---|
| TTS 音频 | cache/tts/ | text hash | 永久 |
| 字幕 SRT/ASS | cache/subtitle/ | text hash | 永久 |
| 渲染临时文件 | cache/render_temp/ | - | 渲染完成后清除 |
| 数据库备份 | database/backup/ | - | 保留最近 3 份 |

### 5.5 错误处理策略

```python
# 分层错误处理
# 1. core 层：抛出具体异常，携带上下文
class AssetNotFoundError(Exception):
    def __init__(self, asset_name: str):
        self.asset_name = asset_name
        super().__init__(f"素材未找到: {asset_name}")

class FFmpegError(Exception):
    def __init__(self, cmd: list[str], stderr: str):
        self.cmd = cmd
        self.stderr = stderr
        super().__init__(f"FFmpeg 执行失败: {stderr[:200]}")

# 2. Pipeline 层：捕获并转化为用户友好的错误消息
# 3. UI 层：弹窗/状态栏显示错误，不崩溃
```

---

## 六、测试步骤详细设计

### 6.1 测试环境准备

```bash
# 创建测试素材目录
mkdir -p tests/fixtures/assets/videos
mkdir -p tests/fixtures/assets/images
mkdir -p tests/fixtures/assets/bgm

# 生成测试用的短视频（使用 FFmpeg 生成测试模式视频）
ffmpeg -y -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 tests/fixtures/assets/videos/test_01.mp4
ffmpeg -y -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 tests/fixtures/assets/videos/test_02.mp4

# 生成测试用音频
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" tests/fixtures/assets/bgm/test_bgm.mp3
```

### 6.2 测试脚本示例（tests/fixtures/scripts/test_script.json）

```json
{
  "title": "测试视频",
  "duration": 15,
  "style": "knowledge",
  "voice": "female_01",
  "bgm": "test_bgm.mp3",
  "segments": [
    {
      "id": 1,
      "text": "这是第一段测试文本",
      "keywords": ["测试"],
      "emotion": "normal",
      "duration": 5
    },
    {
      "id": 2,
      "text": "这是第二段测试文本，表达强烈",
      "keywords": ["测试"],
      "emotion": "strong",
      "duration": 5
    },
    {
      "id": 3,
      "text": "这是最后一段测试文本",
      "keywords": ["测试"],
      "emotion": "calm",
      "duration": 5
    }
  ]
}
```

### 6.3 测试执行命令

```bash
# 全部测试
pytest tests/ -v --tb=short

# 带覆盖率
pytest tests/ --cov=core --cov-report=term --cov-report=html

# 跳过需要 FFmpeg 的测试
pytest tests/ -v -m "not needs_ffmpeg"

# 只运行标记为 slow 的测试
pytest tests/ -v -m "slow"

# GUI 测试（需显示器）
pytest tests/ -v -m "gui"
```

### 6.4 测试验收标准

| 等级 | 标准 | 通过条件 |
|---|---|---|
| P0 | 单元测试 | 全部通过 |
| P1 | 集成测试 | 核心流程正确 |
| P2 | E2E 测试 | 完整管线输出可播放视频 |
| P3 | 性能测试 | 1 分钟视频渲染 < 10 分钟 |
| P4 | GUI 测试 | 所有交互不崩溃 |

---

## 七、交付物清单

### 7.1 最终交付物

| 编号 | 交付物 | 路径 | 备注 |
|---|---|---|---|
| 1 | 主程序入口 | `app.py` | 可直接 `python app.py` 运行 |
| 2 | 核心逻辑模块 | `core/*.py` | 11 个模块 |
| 3 | GUI 界面模块 | `ui/*.py` | 8 个模块 |
| 4 | 配置文件 | `config.yaml` | 默认配置，用户可编辑 |
| 5 | 依赖清单 | `requirements.txt` | pip 一键安装 |
| 6 | 测试套件 | `tests/*.py` | 单元/集成/E2E 测试 |
| 7 | 测试素材 | `tests/fixtures/` | 自动化测试用 |
| 8 | 示例脚本 | `scripts/*.json` | 2-3 个预置示例 |
| 9 | 项目文档 | `README.md` | 安装与使用说明 |
| 10 | Windows 安装包 | `dist/ClipForge_Setup.exe` | PyInstaller + NSIS 打包 |

### 7.2 里程碑

| 里程碑 | 时间 | 交付物 | 验收标准 |
|---|---|---|---|
| M0 骨架 | Day 1 | 项目结构 + 空窗口 | `python app.py` 显示窗口 |
| M1 数据层 | Day 3 | models + database | 单元测试通过 |
| M2 素材系统 | Day 5 | scanner + matcher | 可扫描/搜索素材 |
| M3 规则+Timeline | Day 7 | rules + timeline | 脚本→Timeline 构建 |
| M4 TTS+字幕 | Day 10 | tts + subtitle | 配音/字幕生成 |
| M5 渲染 | Day 13 | ffmpeg + renderer | 10 秒测试视频可输出 |
| M6 管线 | Day 16 | pipeline | 脚本→视频全自动 |
| M7 MVP GUI | Day 20 | 主窗口 + 脚本编辑器 | 基本交互可用 |
| M8 完整 GUI | Day 24 | 所有 GUI 模块 | 全功能可用 |
| M9 测试完成 | Day 28 | 测试报告 | 覆盖率 > 80% |
| M10 发布 | Day 30 | 安装包 | 可安装运行 |

---

## 八、风险与缓释

| 风险 | 概率 | 影响 | 缓释措施 |
|---|---|---|---|
| FFmpeg 转场效果复杂 | 中 | 开发延期 | MVP 仅实现 cut/fade，slide 放后续 |
| EdgeTTS 联网依赖 | 高 | 离线不可用 | 提供 pyttsx3 降级方案 |
| Whisper 首次下载慢 | 中 | 用户体验差 | 首次启动后台下载 + 进度提示 |
| 素材库大时扫描慢 | 低 | 启动慢 | 增量扫描 + 异步执行 |
| GUI 渲染复杂 | 中 | Timeline 视图开发难 | 先用简单 QListWidget，后续升级 |
| FFmpeg 版本兼容 | 低 | 部分命令失效 | 使用基础参数，避免新版特性 |
| 内存不足 | 低 | 渲染失败 | 分段渲染 + 内存监控提示 |
| 字形/字体缺失 | 中 | 字幕乱码 | ASS 嵌入字体或使用系统字体 |

---

## 九、免费素材获取建议

### 9.1 视频素材

| 网站 | 许可证 | 搜索建议 |
|---|---|---|
| [Pexels](https://www.pexels.com) | 免费商用 | "business", "nature", "city", "food", "fitness" |
| [Pixabay](https://pixabay.com/videos/) | 免费商用 | 同上，下载 MP4 格式 |
| [Mixkit](https://mixkit.co) | 免费商用 | 分类浏览，可直接下载 |
| [Coverr](https://coverr.co) | 免费商用 | 适合背景视频 |

### 9.2 背景音乐

| 网站 | 许可证 | 说明 |
|---|---|---|
| [Mixkit Music](https://mixkit.co/free-stock-music/) | 免费商用 | 分类清晰，有情绪标签 |
| [Pixabay Music](https://pixabay.com/music/) | 免费商用 | 搜索 "corporate", "ambient", "upbeat" |
| [Freesound](https://freesound.org) | 需署名 | 搜索时过滤 CC0 授权 |

### 9.3 下载示例脚本（批处理文件）

创建 `download_sample_assets.bat`（可选）：

```batch
@echo off
echo 请手动从以下链接下载示例素材到 assets/ 目录:
echo.
echo 视频:
echo   https://www.pexels.com/video/...
echo.
echo BGM:
echo   https://mixkit.co/free-stock-music/...
echo.
echo 或使用以下 FFmpeg 命令生成测试素材:
echo   ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080 assets/videos/test.mp4
echo   ffmpeg -f lavfi -i "sine=frequency=440:duration=30" assets/bgm/test.mp3
```

---

## 附录 A：核心类数据流图

```
Script (JSON)                    Asset (文件系统 + SQLite)
      │                                  │
      ▼                                  ▼
 ┌──────────┐                    ┌──────────────┐
 │  Parser  │                    │   Scanner    │
 └────┬─────┘                    └──────┬───────┘
      │                                  │
      ▼                                  ▼
 ┌──────────┐                    ┌──────────────┐
 │ Matcher  │◄───────────────────│  Database    │
 └────┬─────┘                    └──────────────┘
      │
      ▼
 ┌──────────┐
 │  Rules   │
 └────┬─────┘
      │
      ▼
 ┌──────────┐         ┌──────────┐
 │ Timeline │────────►│  TTS     │
 │  Builder │         └────┬─────┘
 └────┬─────┘              │
      │                    ▼
      │              ┌──────────┐
      │              │Subtitle  │
      │              └────┬─────┘
      │                    │
      ▼                    ▼
 ┌─────────────────────────────┐
 │         Renderer            │
 │  (FFmpeg Pipeline)          │
 └──────────┬──────────────────┘
            │
            ▼
        Output MP4
```

---

## 附录 B：FFmpeg 常用命令参考

### 视频拼接

```bash
# 方法1：concat demuxer（推荐）
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4

# filelist.txt 格式：
# file 'clip1.mp4'
# file 'clip2.mp4'

# 方法2：concat filter（需要重新编码）
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1" \
  output.mp4
```

### 转场

```bash
# xfade 淡入淡出（需 FFmpeg 4.3+）
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "xfade=transition=fade:duration=0.5:offset=4.5" \
  output.mp4

# 注意：offset = clip1 时长 - 转场时长
```

### 字幕叠加

```bash
# ASS 字幕
ffmpeg -i video.mp4 -vf "ass=subtitle.ass" output.mp4

# SRT 字幕
ffmpeg -i video.mp4 -vf "subtitles=subtitle.srt" output.mp4
```

### 音频混合

```bash
# 配音 + BGM 混合
ffmpeg -i video.mp4 -i voice.wav -i bgm.mp3 \
  -filter_complex "[1:a]volume=1.0[a1];[2:a]volume=0.3,adelay=1000|1000,aloop=loop=-1:size=2e5[a2];[a1][a2]amix=inputs=2:duration=first" \
  -c:v copy output.mp4
```

### 音量归一化

```bash
ffmpeg -i input.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 output.wav
```


> 文档版本：v1.0
> 最后更新：2026-05-24
> 关联架构文档：`docs/lightweight_ai_video_studio_architecture_cn.md`
