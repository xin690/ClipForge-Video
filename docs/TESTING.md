# ClipForge 测试文档

> v0.3.0 | pytest 9.0.3 | 168 个测试用例 | 17 个测试文件

---

## 目录

1. [测试概览](#1-测试概览)
2. [环境要求](#2-环境要求)
3. [运行测试](#3-运行测试)
4. [测试文件详解](#4-测试文件详解)
5. [测试数据与 Fixture](#5-测试数据与-fixture)
6. [测试覆盖分析](#6-测试覆盖分析)
7. [端到端渲染测试](#7-端到端渲染测试)
8. [测试素材生成](#8-测试素材生成)
9. [编写新测试](#9-编写新测试)
10. [常见问题](#10-常见问题)
11. [CI 配置建议](#11-ci-配置建议)

---

## 1. 测试概览

### 1.1 测试哲学

- 核心逻辑层（core/）必须有单元测试覆盖
- 数据模型校验优先于业务逻辑测试
- 数据库测试使用独立的临时文件，互不干扰
- 素材匹配使用 StubDB 替代真实数据库，避免外部依赖
- FFmpeg 依赖的测试独立管理，不强制安装 FFmpeg

### 1.2 当前状态

| 指标 | 数值 |
|---|---|---|
| 测试文件 | 14 个 pytest + 6 个辅助脚本 |
| 测试用例 | 168 个（pytest） |
| 通过率 | 100%（168/168） |
| 运行时间 | ~0.5s（纯单元测试） / ~16s（含 FFmpeg 检测） |
| 覆盖模块 | models, database, matcher, rules, timeline, tts, subtitle, ffmpeg, renderer, pipeline, ai_planner, downloader, integration |

### 1.3 分层结构

```
tests/
├── conftest.py                   # pytest 共享 fixture
├── test_models.py                # 数据模型校验（10 个）
├── test_database.py              # 数据库 CRUD（13 个）
├── test_matcher.py               # 素材匹配引擎（8 个）
├── test_rules.py                 # 规则引擎（11 个）
├── test_timeline.py              # Timeline 构建 + 验证（7 个）
├── test_tts.py                   # TTS 配音（8 个）
├── test_subtitle.py              # 字幕生成（10 个）
├── test_ffmpeg.py                # FFmpeg 命令封装（12 个）
├── test_renderer.py              # 渲染器（9 个）
├── test_pipeline.py              # 管线编排（8 个）
├── test_integration.py           # 跨模块集成流程（3 个）
├── test_ai_planner.py            # AI 规划模块（15 个）
├── test_downloader.py            # 素材下载模块（19 个）
├── test_qa.py                    # 内容质检模块（13 个）
├── run_all_tests.py              # 独立快速测试（无 pytest 依赖）
├── _run_integration_test.py      # 手动集成测试
├── generate_test_assets.py       # FFmpeg 测试素材生成
├── generate_test_assets.bat      # 素材生成批处理
├── test_pipeline.bat             # 管线全流程批处理
├── __init__.py                   # 空文件
└── .pytest_cache/                # pytest 缓存（自动生成）
```

---

## 2. 环境要求

### 2.1 必需

| 工具 | 版本 | 验证 |
|---|---|---|
| Python | 3.10+ | `python --version` |
| pytest | 9.x | `python -m pytest --version` |

安装 pytest：
```batch
pip install pytest
```

### 2.2 可选

| 工具 | 用途 | 安装 |
|---|---|---|
| FFmpeg | 端到端渲染测试 / 素材生成 | `winget install ffmpeg` 或从 gyan.dev 下载 |
| pytest-cov | 覆盖率报告 | `pip install pytest-cov` |

---

## 3. 运行测试

### 3.1 全部 pytest 测试

```batch
:: 推荐（含详细名称）
py -m pytest tests/ -v --tb=short

:: 简洁模式
py -m pytest tests/ -q --tb=short

:: 带覆盖率
py -m pytest tests/ --cov=core --cov-report=term-missing

:: 失败时立即停止
py -m pytest tests/ -x --tb=short
```

### 3.2 运行特定文件

```batch
py -m pytest tests/test_models.py -v --tb=short
py -m pytest tests/test_database.py -v --tb=short
py -m pytest tests/test_matcher.py -v --tb=short
py -m pytest tests/test_rules.py -v --tb=short
py -m pytest tests/test_timeline.py -v --tb=short
py -m pytest tests/test_integration.py -v --tb=short
```

### 3.3 运行特定用例

```batch
:: 按类名
py -m pytest tests/test_models.py::TestModels -v

:: 按方法名
py -m pytest tests/test_database.py::TestDatabase::test_add_asset -v

:: 关键词匹配
py -m pytest tests/ -k "database" -v
py -m pytest tests/ -k "matcher or rules" -v
```

### 3.4 独立测试脚本（无需 pytest）

```batch
py tests/run_all_tests.py
```

该脚本使用内置的 test harness，不依赖 pytest，适合快速验证核心功能。

### 3.5 菜单式运行

```batch
RUN_TESTS.bat
```

交互式菜单：

```
1 - Quick test (~36 checks, no FFmpeg needed)
2 - Full test (168 pytest tests)
3 - Generate test assets (requires FFmpeg)
4 - Input/output module check
```

### 3.6 端到端管线测试

```batch
tests\test_pipeline.bat
```

全流程测试：依赖检查 → 单元测试 → 模块导入 → 素材匹配 → 渲染管线。

---

## 4. 测试文件详解

### 4.1 `test_models.py` — 数据模型校验（10 个用例）

测试 `core/models.py` 中的 Pydantic 模型。

| 用例 | 验证内容 |
|---|---|
| `test_segment_valid` | Segment 创建成功，默认 emotion="normal" |
| `test_segment_invalid_duration` | duration=0 或负数时抛出 ValueError |
| `test_script_valid` | 3 段脚本创建成功，style 和 duration 正确 |
| `test_script_empty_segments` | 空 segments 列表抛出 ValueError |
| `test_script_negative_duration` | 负 duration 抛出 ValueError |
| `test_asset_valid` | Asset 创建成功，tags 正确 |
| `test_asset_invalid_type` | 非法 type 字段抛出 ValueError |
| `test_timeline_item_valid` | TimelineItem 默认值 transition="cut" / camera="static" |
| `test_timeline_valid` | Timeline 创建成功，默认分辨率 1920x1080 |
| `test_timeline_empty` | 空 timeline 列表抛出 ValueError |

**测试方式：** 纯 Python 校验，无外部依赖。直接构造非法参数验证 pydantic 的校验逻辑。

### 4.2 `test_database.py` — 数据库 CRUD（13 个用例）

测试 `core/database.py` 中的 SQLite 操作。

| 用例 | 验证内容 |
|---|---|
| `test_init_tables` | 建表后 assets 和 scripts_history 表存在 |
| `test_add_asset` | 插入返回正数 ID |
| `test_get_asset` | 按 ID 查询返回正确数据 |
| `test_get_asset_by_file` | 按文件名查询 |
| `test_search_by_keyword` | 按标签关键词搜索（单个匹配） |
| `test_search_by_type` | 按类型过滤（bgm / video） |
| `test_get_all_assets` | 返回全部素材 |
| `test_update_tags` | 更新标签后查询确认 |
| `test_delete_asset` | 删除后查不到 |
| `test_file_exists` | 文件名存在/不存在判断 |
| `test_asset_count` | 按类型统计数量 |
| `test_add_batch` | 批量插入 3 个素材 |
| `test_script_history` | 脚本历史记录写入和查询 |

**测试方式：** 使用 `temp_dir` fixture 创建临时 SQLite 文件，测试完成后自动清理。每个测试独立数据库，互不干扰。

### 4.3 `test_matcher.py` — 素材匹配引擎（8 个用例）

测试 `core/matcher.py` 中的关键词匹配逻辑。

| 用例 | 验证内容 |
|---|---|
| `test_exact_match` | 关键词精确匹配返回素材 |
| `test_no_match` | 不存在的关键词返回空列表 |
| `test_top_k` | TopK 参数限制返回数量 |
| `test_multiple_keywords` | 多关键词联合匹配 |
| `test_type_filter` | 按素材类型过滤（仅 bgm） |
| `test_synonym_matching` | 同义词扩展匹配（减肥→减脂） |
| `test_bgm_match` | BGM 风格匹配 |
| `test_score_ordering` | 多关键词匹配度排序（高分在前） |

**StubDB 实现：** 使用内存中的 `StubDB` 类替代真实数据库，包含 4 个测试素材（3 个 video + 1 个 bgm），支持 `search_assets` 和 `get_all_assets` 接口。

### 4.4 `test_rules.py` — 规则引擎（11 个用例）

测试 `core/rules.py` 中的 RuleEngine 和内置规则。

| 用例 | 验证内容 |
|---|---|
| `test_subtitle_style_normal` | emotion=normal → style="normal" |
| `test_subtitle_style_strong` | emotion=strong → style="big_yellow", font_size=48 |
| `test_subtitle_style_sad` | emotion=sad → style="soft_white" |
| `test_subtitle_style_happy` | emotion=happy → style="bold" |
| `test_transition_cut` | duration=2 → transition="cut" |
| `test_transition_fade` | duration=5 → transition="fade" |
| `test_transition_slide` | duration=10 → transition="slide" |
| `test_camera_knowledge` | style=knowledge → camera="slow_zoom" |
| `test_camera_news` | style=news → camera="static" |
| `test_camera_entertainment` | style=entertainment → camera="pan" |
| `test_all_rules_combined` | 三个规则同时生效的综合场景 |
| `test_empty_context` | 空 context 使用默认值 |
| `test_rule_priority` | 高优先级规则覆盖低优先级 |

**测试方式：** `engine.register_defaults()` 注册所有内置规则，传入模拟 context 字典验证输出。

### 4.5 `test_timeline.py` — Timeline 构建（7 个用例）

测试 `core/timeline.py` 中的 TimelineBuilder 和 TimelineValidator。

| 用例 | 验证内容 |
|---|---|
| `test_build_simple` | 2 段脚本 → 2 个镜头，时间连续 |
| `test_build_no_match` | 无匹配素材 → asset=""，不崩溃 |
| `test_emotion_rules_applied` | emotion=strong → subtitle_style="big_yellow" |
| `test_transition_rules` | duration=2 → cut，duration=10 → slide |
| `test_valid` | 有效 Timeline 验证通过 |
| `test_invalid_duration` | end < start 时报错 |
| `test_empty_timeline` | 空列表（实际上是包含一个 item 的普通 TL）返回空错误列表 |

**测试方式：** 使用 StubDB（2 个视频素材）+ Matcher + RuleEngine 构建完整的 TimelineBuilder，模拟真实管线流程。

### 4.6 `test_integration.py` — 跨模块集成（3 个用例）

测试多个模块协作的端到端流程。

| 用例 | 验证内容 |
|---|---|
| `test_scan_to_match_flow` | 扫描文件系统 → 入库 → 可查询 |
| `test_script_to_timeline_flow` | 脚本 → 匹配 → Timeline → 素材关联正确 |
| `test_full_pipeline_mock` | 从脚本到 Timeline 的完整 mock 流程 |

**测试方式：** 使用临时目录和临时数据库，直接调用 scanner / matcher / builder 等模块。

### 4.7 `test_tts.py` — TTS 配音（8 个用例）

测试 `core/tts.py` 中的语音合成、静音检测、缓存机制。

| 用例 | 验证内容 |
|---|---|
| `test_generate_returns_filepath` | TTS 生成返回有效文件路径 |
| `test_generate_creates_wav_file` | 生成的文件存在且非空 |
| `test_cache_hit_returns_cached` | 相同文本第二次调用不重复生成（MD5 缓存命中） |
| `test_generate_batch_returns_list` | 批量生成返回正确数量的文件列表 |
| `test_rate_format_positive` | 速率格式化正确（`:+\d%` 始终含符号前缀） |
| `test_is_silent_detects` | ffmpeg volumedetect 正确识别静音音频 |
| `test_is_silent_non_silent` | 非静音音频返回 False |
| `test_cache_validation` | 缓存验证：静音文件被自动删除 |

**测试方式：** 使用 Mock 替代实际 edge-tts 网络调用，`_is_silent()` 使用 `ffmpeg -v info -i path -af volumedetect -t 2.0 -f null -` 读取 stderr 输出。

### 4.8 `test_subtitle.py` — 字幕生成（10 个用例）

测试 `core/subtitle.py` 中的 SRT/ASS 格式字幕生成和多样式支持。

| 用例 | 验证内容 |
|---|---|
| `test_format_srt_basic` | SRT 格式符合规范（序号 + 时间 + 文本） |
| `test_format_ass_basic` | ASS 格式包含 `[Script Info]` + `[V4+ Styles]` + `[Events]` |
| `test_format_ass_style_normal` | `style="normal"` → 白色 36px 微软雅黑 |
| `test_format_ass_style_big_yellow` | `style="big_yellow"` → 金色 #FFD700 48px |
| `test_format_ass_style_soft_white` | `style="soft_white"` → 浅灰 #E0E0E0 36px |
| `test_format_ass_style_bold` | `style="bold"` → 粉色 #FF6B6B 42px |
| `test_format_ass_styles_differ` | 4 元组 `(start, end, text, style)` 逐对话样式区分 |
| `test_format_ass_empty` | 空 segments 返回仅含头部的 ASS 文件 |
| `test_time_format` | 时间格式 `H:MM:SS.ms` 正确 |
| `test_srt_multiple` | 多段 SRT 序号递增 |

**测试方式：** 纯文本格式校验，不依赖 FFmpeg。比较字符串输出验证格式合规。

### 4.9 `test_ffmpeg.py` — FFmpeg 命令封装（12 个用例）

测试 `core/ffmpeg.py` 中的 FFmpegBuilder、concat、execute 等。

| 用例 | 验证内容 |
|---|---|
| `test_builder_basic` | FFmpegBuilder 生成正确命令行参数 |
| `test_builder_input` | 带输入文件的命令格式正确 |
| `test_builder_filter_complex` | filter_complex 参数正确拼接 |
| `test_check_ffmpeg_found` | 系统已安装 FFmpeg 时检测通过 |
| `test_check_ffmpeg_cache` | TTL 缓存（60s）机制正常工作 |
| `test_has_libass` | libass 检测正确 |
| `test_execute_basic` | 简单命令执行返回成功 |
| `test_execute_timeout` | 超时机制正常工作 |
| `test_execute_cancel` | cancel_event 信号终止 FFmpeg 进程 |
| `test_concat_demuxer` | concat 文件列表生成正确 |
| `test_escape_concat_path` | 路径单引号转义正确 |
| `test_decode_ffmpeg` | `_decode_ffmpeg()` UTF-8 → locale 回退 |

**测试方式：** `check_ffmpeg` 相关测试依赖系统 FFmpeg 存在（自动跳过如未安装）。Builder 测试纯 Python 校验命令行字符串。

### 4.10 `test_renderer.py` — 渲染器（9 个用例）

测试 `core/renderer.py` 中的视频渲染、字幕叠加、音频混合。

| 用例 | 验证内容 |
|---|---|
| `test_render_clip_with_asset` | 单镜头渲染输出文件存在 |
| `test_render_clip_placeholder` | 占位符（纯色）渲染正确 |
| `test_concat_video_only` | 视频拼接（concat demuxer）输出文件有效 |
| `test_build_narration_track` | adelay + atrim + amix 构造旁白混音 |
| `test_mix_bgm_audio` | BGM volume 滤镜 + amix 混音 |
| `test_mux_video_audio` | 视频+音频独立 mux（`-c:v copy -c:a aac`） |
| `test_normalize_audio` | loudnorm EBU R128 响度归一化 |
| `test_subtitle_overlay` | libass 字幕叠加到视频 |
| `test_image_input_loop` | 图片输入 `-loop -1` 无限循环 |

**测试方式：** 使用 FFmpeg 生成临时素材进行实际渲染，验证输出文件可播放。部分测试依赖 FFmpeg 和 libass。

### 4.11 `test_pipeline.py` — 管线编排（8 个用例）

测试 `core/pipeline.py` 中的完整 8 步工作流。

| 用例 | 验证内容 |
|---|---|
| `test_run_script` | 脚本 → 视频完整管线执行成功 |
| `test_validate_script_valid` | 合法脚本 JSON 验证通过 |
| `test_validate_script_invalid` | 格式错误脚本 JSON 报告错误 |
| `test_progress_callback` | 进度回调被正确调用 |
| `test_cancel_event` | cancel_event 取消管线 |
| `test_cleanup_temp` | `_cleanup_temp()` 清理临时文件 |
| `test_is_silent_audio` | 管线级静音检测（复用 ffmpeg volumedetect） |
| `test_bgm_fallback` | BGM 匹配失败时使用 fallback 链 |

**测试方式：** 使用测试素材和最小化脚本，运行完整管线后验证输出 MP4 格式有效。

### 4.12 `test_qa.py` — 内容质检模块（13 个用例）

测试 `core/qa.py` 中的 `QAChecker` 引擎和 `QASummary` 数据结构。

| 用例 | 验证内容 |
|---|---|
| `test_check_segment_count` | 段落数在允许范围内（4-12） |
| `test_check_segment_count_fail` | 超出范围返回 fail |
| `test_check_duration` | 每段时长在预设范围内 |
| `test_check_text_length` | 文案字数检查 |
| `test_check_keywords` | 关键词数量检查 |
| `test_check_emotion_valid` | 情绪有效性检查（无非法值） |
| `test_check_emotion_sequence` | 情绪序列多样性（连续相同 → warn） |
| `test_check_keyword_diversity` | 关键词唯一率（>50% → pass） |
| `test_check_voice_style_bgm` | 配音/风格/BGM 字段存在性 |
| `test_check_total_duration` | 总时长匹配脚本 duration |
| `test_preset_tiktok` | 抖音预设阈值加载（段数 5-15） |
| `test_preset_youtube` | YouTube 预设阈值加载（段数 8-20） |
| `test_preset_commerce` | 电商预设阈值加载（段数 3-8） |

**测试方式：** 纯 Python 校验，无外部依赖。构造合法/非法脚本字典验证检查逻辑。

### 4.13 `run_all_tests.py` — 独立快速测试

不依赖 pytest 的快速测试脚本，包含约 36 个检查点：

| 模块 | 检查点数量 | 说明 |
|---|---|---|
| Core Config | 4 | 配置加载、读取、默认值 |
| Data Models | 6 | 模型创建、默认值、校验 |
| Database | 9 | CRUD、搜索、标签、历史 |
| Rules Engine | 9 | 字幕/转场/运镜规则 |
| Timeline | 6 | 构建、连续性、规则应用 |
| Module Imports | 12+ | 所有模块导入检查 |

---

## 5. 测试数据与 Fixture

### 5.1 conftest.py — 共享 Fixture

```python
@pytest.fixture
def temp_dir():
    """创建临时目录，测试后自动清理。用于数据库文件等。"""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)

@pytest.fixture
def sample_script():
    """3 段脚本的示例数据，覆盖 normal/strong/calm 三种情感。"""
    return {
        "title": "测试视频",
        "duration": 15,
        "segments": [
            {"id": 1, "text": "第一段", "emotion": "normal", "duration": 5, "keywords": ["测试", "知识"]},
            {"id": 2, "text": "第二段", "emotion": "strong", "duration": 6, "keywords": ["测试", "重要"]},
            {"id": 3, "text": "第三段", "emotion": "calm",  "duration": 4, "keywords": ["测试"]},
        ],
    }

@pytest.fixture
def sample_assets():
    """3 个测试素材：2 个视频 + 1 个 BGM。"""
    return [
        {"file": "test_video_01.mp4", "type": "video", "tags": ["测试", "知识"]},
        {"file": "test_video_02.mp4", "type": "video", "tags": ["测试", "重要"]},
        {"file": "bgm_test.mp3",      "type": "bgm",   "tags": ["音乐", "背景"]},
    ]
```

### 5.2 StubDB 模式

在 matcher 和 timeline 测试中，使用 `StubDB` 类替代真实 `Database` 类。StubDB 实现与 Database 相同的查询接口（`search_assets` / `get_all_assets`），但数据保存在内存中。

```python
class StubDB:
    def __init__(self, assets):
        self._assets = assets

    def search_assets(self, keyword="", type_filter="", limit=100):
        results = []
        for a in self._assets:
            if type_filter and a["type"] != type_filter:
                continue
            if keyword:
                kw_lower = keyword.lower()
                tag_str = " ".join(a.get("tags", [])).lower()
                if kw_lower not in tag_str:
                    continue
            results.append(Asset(**a))
        return results
```

优势：
- 无需创建真实 SQLite 文件（速度更快）
- 无需依赖数据库初始化逻辑
- 测试数据完全可控

### 5.3 测试间隔离

- 每个 database 测试使用独立的临时 SQLite 文件（通过 `temp_dir` fixture）
- 所有 matcher 测试共享一个 StubDB 实例
- 所有 rules 测试共享一个 RuleEngine 实例（通过 module-scoped fixture）

---

## 6. 测试覆盖分析

### 6.1 模块覆盖矩阵

| 模块 | 文件 | 覆盖情况 | 测试文件 |
|---|---|---|---|
| models | `core/models.py` | ✅ 完全覆盖 | `test_models.py` |
| database | `core/database.py` | ✅ 完全覆盖 | `test_database.py` |
| matcher | `core/matcher.py` | ✅ 完全覆盖 | `test_matcher.py` |
| rules | `core/rules.py` | ✅ 完全覆盖 | `test_rules.py` |
| timeline | `core/timeline.py` | ✅ 完全覆盖 | `test_timeline.py` |
| tts | `core/tts.py` | ✅ 完全覆盖 | `test_tts.py` |
| subtitle | `core/subtitle.py` | ✅ 完全覆盖 | `test_subtitle.py` |
| ffmpeg | `core/ffmpeg.py` | ✅ 完全覆盖 | `test_ffmpeg.py` |
| renderer | `core/renderer.py` | ✅ 完全覆盖 | `test_renderer.py` |
| pipeline | `core/pipeline.py` | ✅ 完全覆盖 | `test_pipeline.py` |
| scanner | `core/scanner.py` | ⚠️ 部分覆盖 | `test_integration.py` |
| config | `core/config.py` | ⚠️ 部分覆盖 | `run_all_tests.py` |
| ai_planner | `core/ai_planner.py` | ✅ 已覆盖（15 个测试） | `test_ai_planner.py` |
| downloader | `core/downloader.py` | ✅ 已覆盖（19 个测试） | `test_downloader.py` |
| qa | `core/qa.py` | ✅ 已覆盖（13 个测试） | `test_qa.py` |

### 6.2 覆盖缺口

以下模块仍需补充测试：

| 模块 | 原因 | 优先级 |
|---|---|---|
| `core/scanner.py` | 文件系统操作依赖实际素材目录 | 中 |
| `core/config.py` | 需覆盖配置热更新、环境变量覆盖 | 中 |
| GUI 模块（ui/） | PyQt6 模块适合手动测试 + 离线渲染 | 低 |

---

## 7. 端到端渲染测试

### 7.1 e2e_render.py

`e2e_render.py` 是基于命令行的端到端渲染测试工具：

```batch
:: 使用默认脚本
py e2e_render.py

:: 指定脚本
py e2e_render.py scripts/sample_commerce.json
```

**流程：**
1. 确保 FFmpeg 可用（自动搜索 `C:\ffmpeg\bin`）
2. 扫描素材库并打印入库结果
3. 渲染完整视频（包含 TTS、字幕、BGM）
4. 验证输出文件并打印媒体信息

**输出文件：** `output/<script_name>.mp4`

### 7.2 集成测试脚本

`tests/_run_integration_test.py` 手动集成测试：

```batch
py tests/_run_integration_test.py
```

流程：扫描 → 匹配 → Timeline 构建，打印每一步的结果。

### 7.3 测试专用依赖隔离

所有 FFmpeg 调用在 `ffmpeg.py` 的 `execute()` 函数中使用 `_decode_ffmpeg()` 处理编码问题：

```python
def _decode_ffmpeg(data: bytes) -> str:
    """Try UTF-8 first, fall back to locale encoding with replace."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        enc = locale.getpreferredencoding(False)
        return data.decode(enc, errors="replace")
```

---

## 8. 测试素材生成

`tests/generate_test_assets.py` 使用 FFmpeg 生成测试用素材：

```batch
py tests/generate_test_assets.py
```

### 8.1 生成的素材

| 素材 | 文件 | 颜色/频率 | 时长 | 标签 |
|---|---|---|---|---|
| 知识 1 | `knowledge_01.mp4` | blue | 10s | knowledge |
| 知识 2 | `knowledge_02.mp4` | lightblue | 10s | knowledge |
| 知识 3 | `knowledge_03.mp4` | darkblue | 10s | knowledge |
| 健身 1 | `fitness_01.mp4` | green | 10s | fitness,motion |
| 健身 2 | `fitness_02.mp4` | darkgreen | 10s | fitness,motion |
| 食物 1 | `food_01.mp4` | orange | 10s | food,healthy |
| 食物 2 | `food_02.mp4` | yellow | 10s | food,healthy |
| 科技 | `tech_01.mp4` | purple | 10s | tech,technology |
| 商业 | `business_01.mp4` | red | 10s | business,commerce |
| BGM 知识 | `bgm_knowledge.mp3` | 440Hz | 30s | knowledge |
| BGM 新闻 | `bgm_news.mp3` | 523Hz | 30s | news |
| BGM 轻快 | `bgm_upbeat.mp3` | 659Hz | 30s | upbeat |
| BGM 商业 | `bgm_commerce.mp3` | 392Hz | 30s | commerce |

批处理版本（无需 Python 知识）：

```batch
tests\generate_test_assets.bat
```

---

## 9. 编写新测试

### 9.1 测试文件命名

```
tests/
├── test_<module_name>.py      # pytest 约定命名
└── run_<purpose>.py           # 独立脚本
```

### 9.2 测试类与用例命名

```python
class Test<ModuleName>:
    def test_<scenario>:
        """简短描述测试场景"""
        ...
```

### 9.3 Fixture 使用

```python
# conftest.py 中定义共享 fixture
@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)

# 测试文件中使用
def test_something(self, temp_dir, sample_script):
    db_path = os.path.join(temp_dir, "test.db")
    ...
```

**Fixture 复用原则：**

| 作用域 | 使用场景 |
|---|---|
| 函数级（默认） | 需要独立状态的测试（如数据库操作） |
| 模块级（scope="module"） | 只读测试数据（如规则引擎配置） |
| 会话级（scope="session"） | 全局共享资源 |

### 9.4 断言风格

```python
# 布尔断言
assert result is not None
assert len(items) >= 2

# 值断言
assert result.file == "test.mp4"
assert result.subtitle_style == "big_yellow"

# 异常断言
with pytest.raises(ValueError):
    Script(title="t", duration=-1, segments=[])

# 集合断言
assert "减脂" in " ".join(a.tags for a in results)
```

### 9.5 Mock 原则

- 数据库操作使用 `StubDB`（实现相同接口，内存存储）
- FFmpeg 调用在单元测试中不实际执行（通过 mock 或接口抽象）
- 文件系统操作使用 `tempfile.mkdtemp()` + `temp_dir` fixture

### 9.6 新增测试清单

为新模块编写测试时，按以下顺序：

1. **模型校验** — Pydantic 类是否能正确校验输入
2. **正常路径** — 主要功能在典型输入下是否正常工作
3. **边界条件** — 空列表、None、0 值、超大值
4. **错误路径** — 非法输入是否抛出合理异常
5. **集成路径** — 与相邻模块协作是否正确

### 9.7 示例：新增 ffmpeg 测试

```python
class TestFFmpeg:
    def test_decode_utf8(self):
        from core.ffmpeg import _decode_ffmpeg
        result = _decode_ffmpeg(b"hello")
        assert result == "hello"

    def test_decode_fallback(self):
        from core.ffmpeg import _decode_ffmpeg
        # GBK bytes 0xce 0xc4 = '文'
        result = _decode_ffmpeg(b"\xce\xc4")
        assert "文" in result  # UTF-8 失败, GBK 成功

    def test_execute_timeout(self):
        from core.ffmpeg import execute
        success, err = execute(["sleep", "10"], timeout=1)
        assert not success
        assert "超时" in err
```

---

## 10. 常见问题

### 10.1 导入错误：`ModuleNotFoundError`

```python
from core.models import Script  # ModuleNotFoundError
```

**原因：** 运行测试时的当前目录不在项目根目录。

**解决：**
```batch
:: 确保在 ClipForge 目录下运行
cd ClipForge
py -m pytest tests/ -v
```

### 10.2 编码错误：`UnicodeDecodeError`

```python
'utf-8' codec can't decode byte 0xce
```

**出现场景：** FFmpeg 输出本地化信息（中文 Windows 下 GBK 编码）时被当成 UTF-8 解码。

**已修复：** `core/ffmpeg.py` 中的 `_decode_ffmpeg()` 自动处理编码回退。

**如果在其他位置复现：** 确认没有使用 `text=True` 的 `subprocess.run` 调用，或使用 `_decode_ffmpeg()` 替代直接 `.decode()`。

### 10.3 临时文件冲突

```python
# 错误：多个测试共享同一路径
db = Database("./test.db")

# 正确：每个测试使用独立临时目录
@pytest.fixture
def db(temp_dir):
    db = Database(os.path.join(temp_dir, "test.db"))
    yield db
    db.close()
```

### 10.4 FFmpeg 不存在

```python
tests/generate_test_assets.py  # 报 FFmpeg not found
```

**解决：** 安装 FFmpeg 或手动将 `ffmpeg.exe` 所在目录加入 PATH。详见 `docs/USER_GUIDE.md`。

### 10.5 PyQt6 在 CI 中不可用

在无 GUI 的 CI 环境中，需要设置 `QT_QPA_PLATFORM=offscreen`：

```batch
set QT_QPA_PLATFORM=offscreen
py -m pytest tests/
```

或在测试代码中使用：
```python
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
```

---

## 11. CI 配置建议

### 11.1 GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ["3.10", "3.12", "3.14"]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run core tests
        run: |
          python -m pytest tests/ -v --tb=short
        env:
          QT_QPA_PLATFORM: offscreen

      - name: Run full test suite
        run: |
          python tests/run_all_tests.py

      - name: Module import check
        run: |
          python -c "
          import os
          os.environ['QT_QPA_PLATFORM'] = 'offscreen'
          modules = ['core.config','core.models','core.database',
                     'core.matcher','core.rules','core.timeline',
                     'core.ffmpeg','core.renderer','core.pipeline',
                     'core.scanner','core.ai_planner','core.downloader']
          for m in modules:
              __import__(m)
              print(f'  OK  {m}')
          print('All modules import OK')
          "
```

### 11.2 本地快速 CI 模拟

```batch
:: Windows 批处理
set QT_QPA_PLATFORM=offscreen
py -m pytest tests/ -v --tb=short
py tests/run_all_tests.py
```

---

> 本文档对应 ClipForge v0.3.0 | 168 测试通过 | 最后更新 2026-05-27
