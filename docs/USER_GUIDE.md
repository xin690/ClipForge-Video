# ClipForge 用户手册

> 轻量级 AI 视频自动剪辑引擎 | v0.4.0
> 适用平台：Windows 10/11
> 中文完整版见：`docs/用户手册.md`
> v0.4.0 新增：情绪调色 + 节拍卡点 + 30+ 转场 + 9 字幕动画 + 内容探针

---

## 目录

1. [项目概述](#1-项目概述)
2. [环境要求](#2-环境要求)
3. [安装与配置](#3-安装与配置)
4. [编译为 EXE](#4-编译为-exe)
5. [项目结构](#5-项目结构)
6. [配置文件](#6-配置文件)
7. [脚本格式](#7-脚本格式)
8. [使用方式](#8-使用方式)
9. [常见问题](#9-常见问题)

---

## 1. 项目概述

ClipForge 是一个轻量级 AI 视频自动剪辑桌面工具。

**核心理念：** AI 负责规划，程序负责执行。

**输入 → 输出：**

```
视频脚本 JSON + 本地素材库（图片、视频、音频）
    ↓
素材匹配 → 规则引擎 → Timeline → 视频归一化(-an) → concat demuxer
    ↓
TTS 配音 → 旁白对齐(adelay+atrim) → BGM 混合 → loudnorm 归一化
    ↓
音视频 mux(-c:v copy -c:a aac) → 字幕叠加(libass/Pillow)
    ↓
成品 MP4 文件（含配音、字幕、转场、BGM）
```

**适用场景：** 知识科普、新闻快讯、口播视频、电商展示、短视频矩阵。

---

## 2. 环境要求

| 项目 | 最低配置 | 推荐配置 |
|---|---|---|
| 操作系统 | Windows 10 | Windows 11 |
| Python | 3.10+ | 3.12+ |
| 内存 | 8 GB | 16 GB |
| 硬盘 | SSD 256 GB | SSD 512 GB |
| GPU | 无要求 | 可选（不必须） |

### 2.1 必需软件

| 软件 | 版本要求 | 用途 |
|---|---|---|
| FFmpeg | 7.0+（推荐 gyan.dev 完整版） | 视频渲染核心引擎 |
| Python | 3.10+ | 运行环境 |

### 2.2 Python 依赖

```
PyQt6>=6.6.0          # GUI 框架
edge-tts>=6.1.0       # TTS 配音（微软神经网络语音，在线）
pyttsx3               # TTS 离线回退（Windows SAPI5）
faster-whisper>=1.0.0 # 字幕识别（可选）
numpy>=1.24.0         # 数据处理
pydantic>=2.5.0       # 数据模型校验
PyYAML>=6.0.1         # 配置管理
Pillow>=10.0.0        # 字幕图像渲染（libass 不可用时回退）
httpx>=0.25.0          # HTTP 请求
```

---

## 3. 安装与配置

### 3.1 安装 FFmpeg

ClipForge 推荐使用 gyan.dev 的完整版 FFmpeg，该版本内置 libass 字幕滤镜支持。

1. 下载：访问 `https://www.gyan.dev/ffmpeg/builds/` 下载 **ffmpeg-release-full.7z**
2. 解压到 `C:\ffmpeg`，确保 `C:\ffmpeg\bin\ffmpeg.exe` 存在
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH（或让 ClipForge 自动检测）

ClipForge 启动时会按以下顺序自动查找 FFmpeg：
```
C:\ffmpeg\bin\ffmpeg.exe  ← 优先
C:\Program Files\DownloadHelper CoApp\ffmpeg.exe
系统 PATH 中的 ffmpeg
```

验证安装：
```batch
ffmpeg -version
```

### 3.2 安装 Python 依赖

```batch
cd ClipForge
pip install -r requirements.txt
pip install pyttsx3 Pillow pyinstaller
```

### 3.3 首次启动

```batch
python app.py
```

首次启动会自动创建 `config.yaml` 和 `database/` 目录。如果 FFmpeg 未找到，窗口会显示警告。

### 3.4 准备素材

在 `assets/` 目录下创建子目录并放入素材文件：

```
assets/
├── videos/      ← 视频素材（.mp4, .mov, .avi 等）
├── images/      ← 图片素材（.jpg, .png 等）
├── bgm/         ← 背景音乐（.mp3, .wav 等）
└── voice/       ← 预设配音（可选）
```

启动 GUI 后，点击 **工具 → 扫描素材库** 或素材管理页面的 **扫描素材库** 按钮，素材会被自动扫描入库并提取标签。

---

## 4. 编译为 EXE

### 4.1 一键编译

双击运行 `BUILD.bat`：

```batch
BUILD.bat
```

脚本自动执行：
1. 查找 Python（优先 `C:\Users\<用户名>\AppData\Local\Python\bin\python.exe`）
2. 安装 PyInstaller
3. 安装 `requirements.txt` 中的依赖
4. 清理旧的 `dist/` 和 `build/` 目录
5. 执行 `pyinstaller clipforge.spec`
6. 复制 `config.yaml`、示例脚本到 `dist/` 目录

编译完成后，可执行文件位于 `dist\ClipForge.exe`（约 75 MB）。

### 4.2 手动编译

```batch
cd ClipForge
pip install pyinstaller
pyinstaller clipforge.spec --noconfirm
```

### 4.3 编译输出结构

```
dist/
├── ClipForge.exe          ← 主程序（双击运行）
├── config.yaml            ← 配置文件
├── scripts/               ← 示例脚本
│   ├── sample_knowledge.json
│   ├── sample_commerce.json
│   └── sample_health.json
└── assets/
    ├── videos/            ← 在此放入视频素材
    └── bgm/               ← 在此放入背景音乐
```

### 4.4 分发准备

将整个 `dist/` 目录打包即可分发给其他 Windows 用户，无需安装 Python。

注意：
- 目标机器需要安装 FFmpeg（或自带 ffmpeg.exe 并配置 PATH）
- 首次运行会在 `dist/` 同级目录下自动创建 `cache/`、`database/`、`output/` 目录

---

## 5. 项目结构

```
ClipForge/
├── app.py                   # 主入口，启动 GUI
├── config.yaml              # 配置文件
├── requirements.txt         # Python 依赖清单
├── clipforge.spec           # PyInstaller 打包配置
├── BUILD.bat                # 一键编译脚本
│
├── core/                    # 核心逻辑层
│   ├── models.py            # Pydantic 数据模型
│   ├── config.py            # 配置管理
│   ├── database.py          # SQLite 数据库
│   ├── scanner.py           # 素材扫描器
│   ├── matcher.py           # 关键词素材匹配引擎
│   ├── rules.py             # 规则引擎（字幕/转场/运镜）
│   ├── timeline.py          # 时间轴构建器 + 校验器
│   ├── tts.py               # TTS 配音（edge-tts + pyttsx3 回退）
│   ├── subtitle.py          # 字幕生成（ASS 格式）
│   ├── ffmpeg.py            # FFmpeg 命令封装 + 执行
│   ├── renderer.py          # 渲染编排器
│   ├── ai_planner.py        # AI 规划层（主题规划 + 搜索关键词）
│   ├── downloader.py        # 素材自动下载（Pexels/Pixabay）
│   ├── qa.py                # 内容质检（脚本检查 + 导出预设）
│   └── pipeline.py          # 完整工作流管线
│   ├── exceptions.py        # ☆v0.4.0 统一异常类（7 个）
│   ├── synonyms.py           # ☆v0.4.0 同义词引擎
│   ├── semantic.py           # ☆v0.4.0 语义匹配映射
│   ├── color.py              # ☆v0.4.0 情绪调色 + LUT
│   ├── analyzer.py           # ☆v0.4.0 ffprobe 内容探针
│   └── rhythm.py             # ☆v0.4.0 librosa 节拍检测
│
├── ui/                      # PyQt6 图形界面
│   ├── main_window.py       # 主窗口
│   ├── script_editor.py     # 脚本编辑器（含 AI 规划按钮）
│   ├── ai_plan_dialog.py    # AI 视频规划对话框（含脚本编辑 + 脚本预览 + 内容检查三 Tab）
│   ├── asset_browser.py     # 素材浏览器
│   ├── timeline_view.py     # 时间轴可视化
│   ├── batch_panel.py       # 批量处理面板
│   ├── preview_panel.py     # 预览面板
│   ├── settings_dialog.py   # 设置对话框（含素材下载标签页）
│   ├── worker.py            # 后台工作线程
│   └── resources.py         # 样式表
│
├── assets/                  # 素材目录
│   ├── videos/
│   ├── images/
│   ├── bgm/
│   └── voice/
│
├── scripts/                 # 示例脚本
├── output/                  # 输出视频目录
├── cache/                   # 缓存（TTS / 渲染临时文件）
├── database/                # SQLite 数据库
│
├── tests/                   # 测试（168 个）
└── docs/                    # 文档
    ├── DEV_PLAN.md          # 开发计划
    └── USER_GUIDE.md        # 本文件
```

---

## 6. 配置文件

`config.yaml` — 所有可配置项：

```yaml
app:
  name: ClipForge
  version: 0.2.0

paths:
  assets: ./assets        # 素材目录
  scripts: ./scripts      # 脚本目录
  output: ./output        # 输出目录
  cache: ./cache          # 缓存目录
  database: ./database/clipforge.db  # 数据库路径

video:
  width: 1920             # 输出视频宽度
  height: 1080            # 输出视频高度
  fps: 30                 # 帧率
  preset: veryfast        # x264 编码预设（ultrafast~veryslow）
  crf: 23                 # 画质（0~51，越小画质越好）

tts:
  engine: edge-tts        # edge-tts（在线）| pyttsx3（离线）
  voice: zh-CN-XiaoxiaoNeural  # 语音角色
  speed: 1.0              # 语速倍率

subtitle:
  engine: text            # text（脚本直接转）| whisper（语音识别）
  whisper_model: tiny     # tiny | base | small | medium | large
  device: cpu             # cpu | cuda

ai:
  enabled: false          # 是否启用 AI 规划
  provider: openai        # openai | qwen | deepseek
  api_key: ""             # API Key
  model: gpt-4o-mini      # 模型名
  max_versions: 2         # 最多保留版本数

downloader:
  provider: pexels        # 素材提供商（pexels / pixabay）
  api_key: ""             # API Key（免费注册: https://www.pexels.com/api/）
  max_per_query: 3        # 每次搜索返回数
  min_width: 1920         # 最低宽度
  timeout: 120            # 下载超时（秒）

bgm:
  volume: 0.3             # BGM 在最终混音中的音量比例（0.0~1.0）

logging:
  level: INFO             # DEBUG | INFO | WARNING | ERROR

# AI 视频规划完整流程（新增）:
#   1. 配置 ai.enabled=true + ai.api_key
#   2. 配置 downloader.api_key（Pexels/Pixabay 免费注册）
#   3. 软件中点击 "AI 规划" → 输入主题文案
#   4. AI 生成脚本分段 + 素材搜索关键词
#   5. 一键下载素材 → 自动归档到 assets/videos/
#   6. 保存脚本 JSON → 扫描素材 → 生成视频
```

---

## 7. 脚本格式

脚本 JSON 定义要生成的视频内容：

```json
{
  "title": "减脂知识科普",
  "duration": 21,
  "style": "knowledge",
  "voice": "female_01",
  "bgm": "bgm_knowledge.mp3",
  "segments": [
    {
      "id": 1,
      "text": "很多人减脂失败，不是因为运动不够，而是饮食结构出了问题。",
      "keywords": ["knowledge"],
      "emotion": "normal",
      "duration": 7
    },
    {
      "id": 2,
      "text": "科学研究表明，控制热量摄入比增加运动消耗更有效。",
      "keywords": ["knowledge"],
      "emotion": "strong",
      "duration": 7
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 视频标题，也是输出文件名的一部分 |
| `duration` | int | 总时长（秒），必须等于各 segment 时长之和 |
| `style` | string | 视频风格：`knowledge` / `news` / `entertainment` / `commerce` |
| `voice` | string | 配音角色名（当前仅用于标识） |
| `bgm` | string | 背景音乐文件名，需存在于 `assets/bgm/` 目录 |
| `segments` | array | 分段列表，至少 1 段 |

### 分段字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 分段序号（从 1 开始） |
| `text` | string | 配音文本（同时作为字幕文本） |
| `keywords` | string[] | 素材匹配关键词 |
| `emotion` | string | 情感风格：`normal` / `strong` / `sad` / `happy` / `calm` |
| `duration` | int | 本段时长（秒），1~60 |

### 情感风格对应的效果

| 情感 | 字幕样式 | 颜色 | 转场倾向 |
|---|---|---|---|
| `normal` | 白色常规 | #FFFFFF | fade |
| `strong` | 大号黄色加粗 | #FFD700 | fade |
| `sad` | 柔和白色 | #E0E0E0 | fade |
| `happy` | 红色加粗 | #FF6B6B | fade |
| `calm` | 柔和白色 | #E0E0E0 | fade |

### 素材匹配说明

- `keywords` 数组中的关键词会与素材标签进行匹配
- 优先匹配精确关键词，其次匹配同义词
- 如果无匹配素材，将使用纯色占位画面
- 标签来自素材文件名和所在目录名（扫描素材时自动提取）

---

## 8. 使用方式

### 8.1 GUI 模式（推荐）

运行 `app.py` 或 `ClipForge.exe`：

```
python app.py
```

#### 主页标签

| 标签页 | 功能 |
|---|---|
| **脚本编辑** | 编写/编辑视频脚本，一键生成视频 |
| **素材管理** | 浏览/搜索/管理素材库 |
| **批量处理** | 批量处理多个脚本 |
| **设置** | 修改全局配置 |

#### 生成视频流程

1. **脚本编辑** 标签页
   - 可以切换到"表单模式"逐段填写，或"JSON 模式"直接编辑 JSON
   - 点击 **验证脚本** 检查格式
   - 点击 **生成视频** 开始渲染

2. 渲染过程中进度条和状态文字会实时更新
3. 完成后弹出提示，可选择打开输出目录

#### 素材管理

- 点击 **扫描素材库** 扫描 `assets/` 目录
- 在搜索框输入关键词过滤素材
- 支持下三角选择类型过滤

#### 批量处理

- 点击 **添加脚本** 选择多个 JSON 脚本文件
- 点击 **开始批量处理** 按序逐个渲染
- 每个脚本显示独立状态（待处理/成功/失败）
- 完成后可一键打开输出目录

### 8.2 命令行模式

用于调试或集成到其他工具链：

```batch
# 完整渲染（扫描 + 渲染 + 验证）
py e2e_render.py scripts/sample_knowledge.json

# 指定脚本
py e2e_render.py scripts/sample_commerce.json
```

输出文件位于 `output/` 目录，文件名与脚本名相同（如 `sample_knowledge.mp4`）。

### 8.3 运行测试

```batch
py -m pytest tests/ -v
```

168 个测试覆盖所有核心模块。

---

## 9. 常见问题

### 9.1 FFmpeg 未找到

```
警告: 未检测到 FFmpeg
```

**解决方法：**
1. 从 https://www.gyan.dev/ffmpeg/builds/ 下载 full 版本
2. 解压到 `C:\ffmpeg`
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量
4. 重启 ClipForge

ClipForge 启动时会自动搜索 `C:\ffmpeg\bin`，无需手动配置 PATH。

### 9.2 渲染失败：编码错误

```
[render_video] 处理失败: 'utf-8' codec can't decode byte 0xce
```

**原因：** 中文 Windows 下 FFmpeg 输出本地化信息，默认编码与 Python 不兼容。

**解决方法：** 该问题已在 v0.1.0 中修复（v0.2.0 包含所有累积修复）。确认使用的是最新代码。

### 9.3 TTS 无声或失败

**可能原因：**
1. **网络问题：** `edge-tts` 需要联网。无网络时会自动回退到 `pyttsx3`（离线 SAPI5）
2. **缓存问题：** 清除 `cache/tts/` 目录后重试

检查配置文件中的 TTS 引擎设置：
```yaml
tts:
  engine: edge-tts    # 改为 pyttsx3 使用离线引擎
```

### 9.4 BGM 音量不合适

修改 `config.yaml`：
```yaml
bgm:
  volume: 0.3    # 0.0（无 BGM）~ 1.0（BGM 与旁白等音量）
```

推荐值：知识类 0.2~0.3，电商类 0.3~0.4，新闻类 0.1~0.2。

### 9.5 字幕显示异常

- ClipForge 优先使用 libass 原生字幕（质量最高）
- 如果 FFmpeg 不支持 libass，自动回退到 Pillow PNG 叠加模式
- 如需 libass 支持，请使用 gyan.dev 的 full 版 FFmpeg

验证 libass 是否可用：
```batch
ffmpeg -filters | findstr ass
```
如果输出中包含 `libass` 则表示支持。

### 9.6 EXE 编译失败

```batch
BUILD.bat
```

常见问题：
1. **Python 未找到：** BUILD.bat 会搜索常见路径，也可手动修改脚本中的 `PYTHON_CMD` 变量
2. **依赖安装失败：** 确保网络通畅，或先在当前 Python 环境中执行 `pip install -r requirements.txt`
3. **磁盘空间不足：** 编译过程需要约 2 GB 临时空间

### 9.7 编译后的 EXE 无法运行

检查 `dist/` 目录结构是否完整：
```
dist/
├── ClipForge.exe
├── config.yaml
└── assets/
    ├── videos/    ← 至少需要存在（可以为空）
    └── bgm/       ← 至少需要存在（可以为空）
```

如果缺少素材目录，EXE 会在渲染时报路径错误。

---

> 本文档对应 ClipForge v0.4.0 | 239 测试通过 | 最后更新 2026-05-28
