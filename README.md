# ClipForge

> 轻量级 AI 视频自动剪辑引擎 | Windows 桌面应用

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green)](https://pypi.org/project/PyQt6/)
[![FFmpeg](https://img.shields.io/badge/Engine-FFmpeg-orange)](https://ffmpeg.org)
[![Tests](https://img.shields.io/badge/Tests-239%2F239-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

ClipForge 不是 AI 视频生成模型，而是 **AI 自动剪辑引擎**。输入主题文案，AI 规划视频内容并自动下载素材；或输入脚本 JSON + 本地素材库，自动输出成品 MP4（含配音、字幕、转场、BGM）。

> AI 负责规划，程序负责执行。

---

## 适用场景

- 知识科普短视频
- 新闻快讯 / 口播视频
- 电商产品展示
- 短视频矩阵批量生产

---

## 功能特性

- **AI 内容规划** — 输入主题文案 → AI 生成脚本分段 + 素材搜索关键词
- **内容质检 (QA)** — 脚本自动检查（段落数/时长/情绪序列/关键词多样性/配音/BGM/总时长）/ 导出预设（tiktok/youtube/commerce）
- **素材自动下载** — Pexels/Pixabay API 搜索 → 一键下载 → 自动归档分类 → 增量扫描入库
- **素材自动匹配** — 关键词标签检索，同义词扩展 + 情绪调性 + 多样性评分 + 语义分类映射<br>v0.4.0 升级：10 因子综合评分算法
- **规则引擎** — 字幕样式、转场效果、运镜自动决策
- **TTS 配音** — edge-tts（在线）→ pyttsx3（离线）→ silent 三级降级
- **自动字幕** — ASS/SRT 格式，4 种样式 + 9 种动画（pulse/swing/slide_up/typewriter/bounce/glow 等）<br>v0.4.0 升级：9 位置灵活调整，每段独立覆写
- **视频渲染** — 视频+音频分离管线，concat demuxer 无缝拼接<br>v0.4.0 升级：30+ 种 xfade 转场，25 对情绪全覆盖
- **画面调色** — 情绪感知段级调色 + LUT 支持 + Ken Burns 可配置缩放 ☆NEW
- **节奏卡点** — librosa BPM 检测 + 节拍对齐，强拍弱拍转场区分 ☆NEW
- **内容探针** — ffprobe 分辨率/帧率/音频属性 + 自动标签 ☆NEW
- **响度归一化** — EBU R128 标准 (loudnorm)
- **运镜效果** — static / slow_zoom / pan
- **GUI 界面** — PyQt6 暗色主题，脚本编辑/素材管理/时间轴/预览/批量处理
- **取消机制** — 渲染中途可取消，临时文件自动清理

---

## 系统架构

```
  ┌─────────────────────────────────────────────────┐
  │                输入方式 A（AI 规划）               │
  │  主题文案 → AI 生成 Script → AI 搜索关键词        │
  │      → 下载素材 → 自动归档 → 扫描入库             │
  └──────────┬──────────────────────────────────────┘
             ↓
  ┌─────────────────────────────────────────────────┐
  │                输入方式 B（手动）                  │
  │        脚本 JSON + 本地素材库                     │
  └──────────┬──────────────────────────────────────┘
             ↓
       素材检索（关键词标签匹配）
             ↓
       规则引擎（字幕/转场/运镜）
             ↓
       Timeline 时间轴构建
             ↓
  ━━━━━━━━ 视频分支 ━━━━━━━━
  镜头归一化(-an, yuv420p, 30fps)
             ↓
  concat demuxer 视频拼接
             ↓
  ━━━━━━━━ 音频分支 ━━━━━━━━
  TTS 配音 → adelay+atrim 旁白对齐
             ↓
  BGM 混合(volume+amix)
             ↓
  loudnorm 响度归一化
             ↓
  ━━━━━━━━ 最终合成 ━━━━━━━━
  音视频 mux (-c:v copy -c:a aac)
             ↓
  字幕叠加 (libass / Pillow)
             ↓
  输出 MP4
```

---

## 快速开始

### 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | 3.10+ |
| FFmpeg | 7.0+ (gyan.dev full build 推荐) |
| 内存 | 8GB+ |

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/xin690/ClipForge-Video.git
cd ClipForge

# 2. 安装依赖
py -m pip install -r requirements.txt

# 3. 复制配置文件
copy config.template.yaml config.yaml

# 4. 安装 FFmpeg (如未安装)
# 从 https://www.gyan.dev/ffmpeg/builds/ 下载 ffmpeg-release-full.7z
# 解压到 C:\ffmpeg，确保 C:\ffmpeg\bin\ffmpeg.exe 存在

# 5. 准备素材
mkdir assets\videos assets\bgm assets\images
# 将视频/BGM/图片放入对应目录

# 6. 启动
py app.py
```

### AI 规划快速上手（NEW）

```bash
# 1. 配置 AI API Key（编辑 config.yaml 或 GUI 设置对话框）
#    ai.enabled: true
#    ai.provider: deepseek   # 或 openai / qwen
#    ai.api_key: "sk-xxxx"

# 2. 配置素材下载 API Key（免费注册 https://www.pexels.com/api/）
#    downloader.provider: pexels
#    downloader.api_key: "xxxx"

# 3. 启动软件，点击脚本编辑器中的「AI 规划」按钮
# 4. 输入主题（例如：「制作一个关于中国自然风光的短视频」）
# 5. 点击「AI 规划」→ 查看生成的分段
# 6. 点击「下载素材」→ 自动搜索并下载
# 7. 点击「保存脚本」→ 自动生成 JSON
# 8. 扫描素材 → 生成视频
```

> 如果没有素材 API Key，可跳过下载步骤。AI 规划只生成脚本 JSON，后续使用本地素材库匹配。

### 命令行模式

```bash
# 端到端渲染
py e2e_render.py scripts/sample_knowledge.json

# 运行测试
py -m pytest tests/ -v --tb=short

# 生成测试素材
py tests/generate_test_assets.py
```

---

## 项目结构

```
ClipForge/
├── app.py                  # GUI 主入口
├── config.template.yaml    # 配置模板（复制为 config.yaml 使用）
├── requirements.txt        # Python 依赖
│
├── core/                   # 核心逻辑层（22 个模块）
│   ├── models.py           # Pydantic 数据模型
│   ├── config.py           # YAML 配置管理
│   ├── database.py         # SQLite 素材库
│   ├── scanner.py          # 素材自动扫描
│   ├── matcher.py          # 关键词素材匹配（10 因子评分）
│   ├── rules.py            # 规则引擎（字幕/转场/运镜）
│   ├── timeline.py         # Timeline 构建 + 校验
│   ├── tts.py              # TTS 配音（三级降级）
│   ├── subtitle.py         # 字幕生成（ASS/SRT + 9 动画）
│   ├── ffmpeg.py           # FFmpeg 命令封装
│   ├── renderer.py         # 视频+音频分离渲染器
│   ├── pipeline.py         # 完整工作流管线
│   ├── ai_planner.py       # AI 规划（主题 → 脚本 + 搜索关键词）
│   ├── downloader.py       # 素材自动下载（Pexels/Pixabay）
│   ├── qa.py               # 内容质检（脚本检查 + 导出预设）
│   ├── exceptions.py       # 统一异常类体系 ☆v0.4.0
│   ├── synonyms.py         # 同义词引擎（编辑距离模糊匹配）☆v0.4.0
│   ├── semantic.py         # 语义匹配（20 组分类映射）☆v0.4.0
│   ├── color.py            # 情绪调色 + LUT + Ken Burns ☆v0.4.0
│   ├── analyzer.py         # ffprobe 内容探针标签 ☆v0.4.0
│   └── rhythm.py           # librosa 节拍检测 + 对齐 ☆v0.4.0
│
├── ui/                     # PyQt6 图形界面（10 个模块）
│   ├── main_window.py      # 主窗口
│   ├── script_editor.py    # 脚本编辑器 + AI 规划按钮
│   ├── ai_plan_dialog.py   # AI 视频规划对话框
│   ├── asset_browser.py    # 素材浏览器
│   ├── timeline_view.py    # 时间轴可视化
│   ├── preview_panel.py    # 视频预览
│   ├── batch_panel.py      # 批量处理
│   ├── settings_dialog.py  # 设置对话框（7 个标签页）
│   ├── worker.py           # 后台线程
│   └── resources.py        # 样式表
│
├── tests/                  # 239 个测试用例（20 个测试文件）
├── docs/                   # 文档（7 篇）
├── scripts/                # 示例脚本
├── assets/                 # 素材目录（用户自行准备）
└── output/                 # 输出视频
```

---

## 脚本格式

```json
{
  "title": "减脂知识科普",
  "duration": 21,
  "style": "knowledge",
  "segments": [
    {
      "id": 1,
      "text": "很多人减脂失败，不是运动不够",
      "keywords": ["减脂", "健身"],
      "emotion": "strong",
      "duration": 7
    }
  ]
}
```

完整格式见 `docs/用户手册.md` 第四章。

---

## 素材准备

### 目录结构

```
assets/
├── videos/      ← 视频素材 (.mp4, .mov, .avi)
├── images/      ← 图片素材 (.jpg, .png)
├── bgm/         ← 背景音乐 (.mp3, .wav)
└── voice/       ← 预设配音（可选）
```

### 标签规则

素材入库时从文件路径自动提取标签：

```
assets/videos/food/healthy_salad.mp4
  → 文件名分割: ["healthy", "salad"]
  → 父目录: "food"
  → 最终标签: ["healthy", "salad", "food"]
```

启动 GUI 后 → 工具 → 扫描素材库，即可入库。

### AI 自动下载素材

使用 AI 规划对话框的「下载素材」功能：
- 需要配置 Pexels API Key（免费注册：https://www.pexels.com/api/）
- AI 为每个分段生成英文搜索词
- 自动搜索匹配视频 → 下载到 `assets/videos/` → 增量扫描入库
- 文件名包含分段编号，便于识别

---

## 编码规格

| 项目 | 规格 |
|------|------|
| 视频编码 | H.264 (libx264), yuv420p |
| 音频编码 | AAC, 44100Hz, stereo |
| 帧率 | 30fps (vf fps=30) |
| GOP | -g 60 -keyint_min 60 |
| 时间基准 | -video_track_timescale 30000 |
| 优化 | -movflags +faststart |

---

## 测试

```bash
py -m pytest tests/ -v --tb=short
```

239 个测试用例，覆盖 22 个核心模块。

---

## 打包为 EXE

```bash
BUILD.bat
# 输出: dist\ClipForge.exe (~75MB)
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [用户手册](docs/用户手册.md) | 完整使用指南（中文），含 AI 规划教程 |
| [开发计划](docs/DEV_PLAN.md) | 开发计划 + 审计结果 + 实施状态 |
| [测试文档](docs/TESTING.md) | 测试覆盖 + 运行说明 |
| [架构方案](docs/lightweight_ai_video_studio_architecture_cn.md) | 技术架构设计 |
| [示例](docs/示例_中国自然风光.md) | 中国自然风光视频制作示例 |

---

## 常见问题

### AI 规划需要什么配置？

在 `config.yaml` 中启用 AI 并填入 API Key：

```yaml
ai:
  enabled: true
  provider: deepseek       # openai / qwen / deepseek
  api_key: "sk-xxxx"
  model: deepseek-chat     # 或 gpt-4o-mini / qwen-plus
```

或在 GUI 中：设置 → AI 标签页 → 勾选「启用 AI 规划」→ 填入 API Key。

### 素材自动下载需要什么？

免费注册 Pexels API Key：https://www.pexels.com/api/

在 `config.yaml` 中配置：

```yaml
downloader:
  provider: pexels
  api_key: "your-pexels-api-key"
```

或在 GUI 中：设置 → 素材下载标签页 → 填入 API Key。

### AI 规划是否会覆盖本地素材？

不会。AI 规划的脚本 JSON 中包含 keywords，后续渲染管线仍使用本地 Matcher 进行素材匹配。如果下载了新素材，扫描后它们也会作为候选参与匹配。

---

## 许可证

MIT License
