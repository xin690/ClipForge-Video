# 轻量级 AI 视频创作系统技术方案（本地低资源版）

## 一、项目目标

构建一个：

- 普通电脑可运行
- 本地优先
- 极低 Token 消耗
- 自动化视频生产
- 支持批量生成
- 可商用扩展

的视频创作系统。

系统输入：

1. 视频脚本 JSON
2. 本地素材库（图片、视频、音频）

系统输出：

1. 自动生成的视频 MP4
2. 自动配音
3. 自动字幕
4. 自动转场
5. 自动 BGM
6. 最终渲染视频

核心设计目标：

> AI 负责规划，程序负责执行。

避免：

- 全 AI 视频生成
- 高显存模型
- 重度多 Agent
- 视频大模型
- 大规模 embedding

采用：

> 本地素材库 + 规则引擎 + 少量 AI + FFmpeg 自动渲染

---

# 二、系统总体架构

系统架构：

```text
输入脚本 JSON
        ↓
素材检索系统
        ↓
规则引擎
        ↓
AI 镜头规划（少量）
        ↓
Timeline 时间轴生成
        ↓
视频渲染：镜头归一化 → concat demuxer 拼接
        ↓
音频生成：TTS 配音 → 旁白对齐(adelay+atrim) → BGM 混合 → loudnorm
        ↓
音视频 mux → 字幕叠加 → 输出 MP4
```

系统核心：

> Timeline（时间轴）生成。

FFmpeg 仅负责执行 Timeline。

---

# 三、系统核心原则

## 1. 不让 AI 理解视频

禁止：

- 上传完整视频给 GPT
- 上传大量图片给 GPT
- 让 GPT 分析素材库

原因：

- Token 极高
- 速度慢
- 不稳定
- 成本高

正确方式：

> 本地提前标签化素材。

---

## 2. AI 只负责“选择”

错误：

```text
让 AI 自动生成整条视频
```

正确：

```text
给 AI 候选素材
让 AI 做选择
```

例如：

输入：

```json
{
  "text": "减脂核心是饮食",
  "assets": [
    "food01.mp4",
    "gym02.mp4"
  ]
}
```

输出：

```json
{
  "asset": "food01.mp4",
  "transition": "zoom",
  "subtitle_style": "strong"
}
```

---

## 3. 程序负责执行

程序负责：

- 视频拼接
- 转场
- 字幕
- 配音
- BGM
- 导出
- 渲染

原因：

- 更稳定
- 更快
- 更低资源
- 可重复
- 可批量化

---

# 四、推荐技术栈

## 核心技术栈

| 模块 | 技术 |
|---|---|
| 主程序 | Python |
| 视频渲染 | FFmpeg |
| 时间轴 | JSON Timeline |
| 数据库 | SQLite |
| TTS | EdgeTTS / Piper |
| 字幕 | faster-whisper |
| AI API | GPT / Qwen API |
| UI | PyQt6 |
| 素材管理 | 本地文件夹 |

---

## 不推荐技术

避免：

| 技术 | 原因 |
|---|---|
| Stable Diffusion 视频 | 显存需求高 |
| Sora 类方案 | 不可本地化 |
| 向量数据库 | 普通电脑负担大 |
| LangChain 多 Agent | 复杂且收益低 |
| 视频理解大模型 | Token 和算力爆炸 |

---

# 五、硬件配置建议

## 最低配置

| 硬件 | 要求 |
|---|---|
| CPU | 4 核 |
| 内存 | 8GB |
| GPU | 无需独显 |
| 硬盘 | SSD |
| 系统 | Windows |

---

## 推荐配置

| 硬件 | 推荐 |
|---|---|
| CPU | i5 / Ryzen 5 |
| 内存 | 16GB |
| GPU | RTX 3050 / 3060 |
| SSD | 512GB |

---

# 六、目录结构设计

推荐目录：

```text
project/
│
├── assets/
│   ├── videos/
│   ├── images/
│   ├── bgm/
│   └── voice/
│
├── scripts/
│   └── xxx.json
│
├── cache/
│
├── output/
│
├── database/
│   └── assets.db
│
├── timeline/
│
├── templates/
│
├── core/
│   ├── planner/
│   ├── renderer/
│   ├── retrieval/
│   ├── subtitle/
│   ├── tts/
│   └── ffmpeg/
│
└── app.py
```

---

# 七、脚本 JSON 设计

推荐结构：

```json
{
  "title": "减脂知识",
  "duration": 60,
  "style": "knowledge",
  "voice": "female_01",
  "bgm": "fitness_fast",
  "segments": [
    {
      "id": 1,
      "text": "很多人减脂失败",
      "keywords": ["减脂", "健身"],
      "emotion": "normal",
      "duration": 5
    },
    {
      "id": 2,
      "text": "不是运动不够，而是饮食错误",
      "keywords": ["饮食", "热量"],
      "emotion": "strong",
      "duration": 6
    }
  ]
}
```

---

# 八、素材系统设计

## 目标

实现：

- 快速素材匹配
- 低资源占用
- 可批量管理
- 不依赖 AI 理解

---

## 素材标签结构

每个素材建立 metadata：

```json
{
  "file": "food01.mp4",
  "type": "video",
  "duration": 8,
  "tags": [
    "减脂",
    "沙拉",
    "低卡"
  ]
}
```

---

## SQLite 数据表设计

### assets

```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    file TEXT,
    type TEXT,
    duration INTEGER,
    tags TEXT
);
```

---

## 素材匹配逻辑

推荐：

```python
if "减脂" in keywords:
    match_assets()
```

而不是：

- embedding
- 向量搜索
- 大模型理解

原因：

- 更轻量
- 更稳定
- 更快
- 更适合普通电脑

---

# 九、规则引擎设计

规则引擎是系统核心之一。

作用：

- 替代大量 AI 推理
- 降低 Token
- 提高稳定性

---

## 示例规则

### 字幕样式

```python
if emotion == "strong":
    subtitle_style = "big_yellow"
```

---

### 转场规则

```python
if duration <= 3:
    transition = "cut"
else:
    transition = "fade"
```

---

### 运镜规则

```python
if style == "knowledge":
    camera = "slow_zoom"
```

---

## 原则

> 能用规则解决的问题，不用 AI。

---

# 十、AI 规划层设计

## AI 的职责

AI 只负责：

1. 镜头选择
2. 节奏规划
3. 文案优化
4. 少量镜头语言

---

## AI 输入（极简）

```json
{
  "text": "减脂核心是饮食",
  "assets": [
    {
      "id": "food01",
      "tags": ["低卡", "沙拉"]
    },
    {
      "id": "gym01",
      "tags": ["跑步", "健身"]
    }
  ]
}
```

---

## AI 输出

```json
{
  "asset": "food01",
  "transition": "fade",
  "subtitle_style": "strong"
}
```

---

## Token 控制策略

### 原则

1. 分段调用
2. 只传 TopK 素材
3. 不传图片
4. 不传完整视频
5. 不传长上下文

---

## 目标成本

单条视频：

```text
1000~3000 tokens
```

---

# 十一、Timeline 时间轴系统

Timeline 是整个系统最核心的数据结构。

---

## Timeline 示例

```json
{
  "timeline": [
    {
      "start": 0,
      "end": 5,
      "asset": "food01.mp4",
      "transition": "fade",
      "subtitle": "减脂核心是饮食",
      "camera": "zoom_in"
    }
  ]
}
```

---

## Timeline 职责

Timeline 负责：

- 镜头顺序
- 时长
- 转场
- 字幕
- 音频
- 运镜

FFmpeg 根据 Timeline 自动执行。

---

# 十二、配音系统设计

## 推荐方案（联网）

### EdgeTTS

优势：

- 免费
- 极轻量
- 效果优秀
- CPU 即可

---

## 离线方案

### Piper TTS

优势：

- 本地运行
- 内存占用低
- CPU 可运行

---

## 工作流

```text
脚本文本
    ↓
TTS
    ↓
wav/mp3
    ↓
音量归一化
    ↓
输出配音
```

---

# 十三、字幕系统设计

## 推荐方案

### faster-whisper tiny/base

原因：

- 轻量
- 快速
- CPU 可运行
- 精度足够

---

## 输出格式

```text
.srt
.ass
```

---

# 十四、FFmpeg 渲染系统

FFmpeg 是整个系统执行层核心。

---

## FFmpeg 职责

负责：

- 拼接视频
- 添加字幕
- 添加 BGM
- 转场
- 缩放
- 导出 MP4

---

## 推荐编码参数

### 1080P

```bash
-c:v libx264
-pix_fmt yuv420p
-preset veryfast
-crf 23
-ar 44100
-ac 2
-g 60 -keyint_min 60 -sc_threshold 0
-video_track_timescale 30000
-movflags +faststart
```

---

## 推荐分辨率

| 类型 | 推荐 |
|---|---|
| 短视频 | 1080x1920 |
| 普通视频 | 1920x1080 |
| 低资源 | 1280x720 |

---

## 推荐转场

仅使用轻量转场：

- fade
- cut
- slide
- zoom

避免：

- AI 特效
- 光流
- 粒子系统

---

# 十五、资源占用估算

## 生成 1 分钟视频

| 模块 | 占用 |
|---|---|
| Python | <300MB |
| FFmpeg | 1~2GB |
| Whisper tiny | <1GB |
| EdgeTTS | 极低 |

---

## 总体要求

```text
8GB 内存即可运行
```

---

# 十六、MVP 最小可行版本

第一阶段只实现：

```text
脚本 JSON
    ↓
素材自动匹配
    ↓
自动配音
    ↓
自动字幕
    ↓
FFmpeg 自动导出
```

不要一开始就做：

- AI 导演
- AI 运镜
- AI 视频生成
- 多 Agent
- 自动故事创作

---

# 十七、后续可扩展能力

## 第二阶段

### 1. 自动节奏卡点

根据 BGM 自动切镜。

---

### 2. 自动封面生成

本地 SDXL。

---

### 3. 自动情绪曲线

根据文案自动调整：

- 字幕
- 转场
- 运镜
- BGM

---

### 4. 批量视频生产

支持：

```text
100~1000 条视频/天
```

---

# 十八、产品定位

系统定位：

> AI 自动剪辑引擎

而不是：

> AI 视频生成模型

---

## 适合的视频类型

### 推荐

- 知识类
- 新闻类
- 口播类
- 电商类
- 混剪类
- 短视频矩阵

---

### 不推荐

- AI 电影
- 长剧情视频
- 高级影视特效
- AI 原创动画

---

# 十九、系统核心优势

## 1. 普通电脑可运行

无需高显卡。

---

## 2. 极低 Token 成本

AI 仅做决策。

---

## 3. 稳定性高

FFmpeg 可控。

---

## 4. 可批量化

适合矩阵生产。

---

## 5. 开发难度适中

传统工程占主导。

---

# 二十、最终结论

最终推荐架构：

```text
本地素材库
+
规则引擎
+
少量 AI 规划
+
Timeline 时间轴
+
FFmpeg 自动渲染
```

系统核心思想：

> AI 不负责生成视频。

而是：

```text
AI 负责：
- 理解
- 规划
- 决策
```

```text
程序负责：
- 执行
- 渲染
- 导出
```

这是：

- 最低资源
- 最稳定