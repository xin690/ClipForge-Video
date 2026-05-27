# ClipForge 测试指南 (v0.2.0)

## 测试层级总览

```
Level 1: 单元测试 ─── pytest (自动化，无依赖)
Level 2: 模块导入 ─── 验证 22 个模块可导入 (自动化)
Level 3: 集成测试 ─── 素材扫描 + 匹配 + Timeline 构建 (自动化)
Level 4: 管线 E2E ─── 脚本 → 视频完整流程 (半自动化，需 FFmpeg)
Level 5: GUI 测试 ─── 手动操作验证
Level 6: 性能测试 ─── 资源消耗基准
```

---

## Level 1: 单元测试（完全自动化）

```bash
# 运行全部 168 个测试
pytest tests/ -v --tb=short

# 带覆盖率报告
pytest tests/ --cov=core --cov-report=html --cov-report=term

# 单独测试某个模块
pytest tests/test_database.py -v
pytest tests/test_matcher.py -v
pytest tests/test_rules.py -v
pytest tests/test_timeline.py -v
pytest tests/test_models.py -v
pytest tests/test_integration.py -v
```

**测试覆盖范围：**

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| `test_models.py` | 10 | Pydantic 模型校验、字段约束、类型检查 |
| `test_database.py` | 13 | SQLite CRUD、搜索、统计、批量操作 |
| `test_matcher.py` | 8 | 关键词匹配、同义词、排序、TopK |
| `test_rules.py` | 11 | 规则引擎、优先级、字幕/转场/运镜决策 |
| `test_timeline.py` | 7 | Timeline 构建、校验、规则集成 |
| `test_tts.py` | 8 | TTS 配音、静音检测、缓存、速率 |
| `test_subtitle.py` | 10 | ASS/SRT 格式、多样式、4 元组 |
| `test_ffmpeg.py` | 12 | FFmpegBuilder、concat、xfade、execute |
| `test_renderer.py` | 9 | 渲染编排、字幕叠加、音频混合 |
| `test_pipeline.py` | 8 | 完整管线编排、错误处理、取消 |
| `test_integration.py` | 3 | 跨模块集成场景 |

---

## Level 2: 模块导入测试

```bash
# 验证所有模块可正常导入
python -c "
import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'
modules = ['core.config','core.models','core.database','core.matcher',
    'core.rules','core.timeline','core.tts','core.subtitle',
    'core.ffmpeg','core.renderer','core.pipeline','core.scanner',
    'core.ai_planner','core.downloader',
    'ui.resources','ui.worker','ui.main_window','ui.script_editor',
    'ui.asset_browser','ui.timeline_view','ui.batch_panel','ui.settings_dialog',
    'ui.ai_plan_dialog']
for m in modules:
    __import__(m)
    print(f'OK {m}')
print(f'All {len(modules)} modules imported successfully')
"
```

---

## Level 3: 集成测试

### 3.1 素材扫描 + 数据库

```bash
# 生成测试素材后运行
python -c "
from core.config import load_config; load_config()
from core.database import Database
from core.scanner import AssetScanner

db = Database('./database/test_integration.db')
db.init_tables()

scanner = AssetScanner(db, './assets')
count = scanner.scan_all()
deleted = scanner.remove_deleted()

all_assets = db.get_all_assets()
counts = db.get_asset_count()
print(f'素材总数: {counts[\"total\"]}')
print(f'视频: {counts.get(\"video\", 0)}')
print(f'BGM: {counts.get(\"bgm\", 0)}')
print(f'新增: {count}, 清理: {deleted}')

db.close()
"
```

### 3.2 关键词匹配测试

```bash
python -c "
from core.config import load_config; load_config()
from core.database import Database
from core.matcher import Matcher

db = Database('./database/test_integration.db')
db.init_tables()
matcher = Matcher(db)

# 测试匹配
results = matcher.match('减脂知识', ['减脂', '饮食'], top_k=5)
for r in results:
    tags = ', '.join(r.tags)
    print(f'  [{r.type}] {r.file} → tags: {tags}')

db.close()
"
```

### 3.3 Timeline 构建测试

```bash
python -c "
from core.config import load_config; load_config()
from core.database import Database
from core.matcher import Matcher
from core.rules import RuleEngine
from core.timeline import TimelineBuilder, TimelineValidator
from core.models import Script

db = Database('./database/test_integration.db')
db.init_tables()
matcher = Matcher(db)
rules = RuleEngine()
rules.register_defaults()
builder = TimelineBuilder(matcher, rules)

script = Script(
    title='测试', duration=15, style='knowledge',
    segments=[
        {'id': 1, 'text': '减脂核心是饮食', 'keywords': ['减脂'], 'emotion': 'strong', 'duration': 5},
        {'id': 2, 'text': '运动也很重要', 'keywords': ['健身'], 'emotion': 'normal', 'duration': 5},
    ],
)
timeline = builder.build(script)

validator = TimelineValidator()
errors = validator.validate(timeline)
if errors:
    print(f'校验错误: {errors}')
else:
    print('Timeline 校验通过')

for i, item in enumerate(timeline.timeline):
    print(f'镜头 {i+1}: {item.asset} | {item.transition} | {item.subtitle_style} | {item.start:.1f}s-{item.end:.1f}s')

db.close()
"
```

---

## Level 4: 端到端管线测试

### 前提条件
1. FFmpeg 已安装
2. 已生成测试素材（运行 `tests\generate_test_assets.bat`）
3. 示例脚本已存在（`scripts/` 目录）

### 完整管线测试

```bash
python -c "
from core.config import load_config; load_config()
from core.pipeline import Pipeline, PipelineProgress
from core.database import Database
from core.scanner import AssetScanner

# 1. 扫描素材
db = Database('./database/clipforge.db')
db.init_tables()
scanner = AssetScanner(db, './assets')
scanner.scan_all()
db.close()

# 2. 执行管线
pipeline = Pipeline()
def on_progress(p: PipelineProgress):
    print(f'[{p.step.value}] {p.message} ({p.progress*100:.0f}%)')

result = pipeline.run('./scripts/sample_knowledge.json', './output/e2e_test.mp4', on_progress)
print(f'\\n输出: {result}')

import os
size = os.path.getsize(result)
print(f'文件大小: {size/1024:.1f} KB')
"
```

### 批量处理测试

```bash
python -c "
from core.config import load_config; load_config()
from core.pipeline import Pipeline
from pathlib import Path

pipeline = Pipeline()
script_files = [str(f) for f in Path('./scripts').glob('*.json')]
Path('./output/batch').mkdir(parents=True, exist_ok=True)

results = pipeline.run_batch(script_files, './output/batch')
for path, success, msg in results:
    status = '✓' if success else '✗'
    print(f'{status} {Path(path).name}: {msg}')
"
```

---

## Level 5: GUI 手动测试清单

### 5.1 启动测试

```
□ 双击 RUN_LOCAL.bat，GUI 无报错启动
□ 窗口标题显示 "ClipForge - AI 视频剪辑引擎 v0.2.0"
□ 菜单栏显示：文件、工具、设置、帮助
□ Tab 栏显示：脚本编辑、素材管理、批量处理
□ 状态栏显示 "素材: 0" 或正确数量
```

### 5.2 素材管理测试

```
□ 点击「扫描素材库」，状态栏显示扫描进度
□ 素材表格显示正确文件列表（文件名、类型、时长、标签）
□ 搜索框输入关键词，表格实时过滤
□ 类型下拉框选择 video/bgm，表格过滤
□ 导入素材按钮可正常选择并复制文件
```

### 5.3 脚本编辑测试

```
□ 「新建」按钮生成默认脚本模板
□ JSON 编辑器语法高亮正常（键名蓝色、字符串绿色、数字橙色）
□ 「打开」按钮可加载 scripts/ 下示例脚本
□ 「验证」按钮通过时显示绿色提示
□ 表单模式显示正确的分段列表
□ 表单修改后点击「从表单更新 JSON」同步到编辑器
□ 添加/删除分段按钮正常工作
```

### 5.4 视频生成测试

```
□ 点击「生成视频」按钮，按钮变为「取消」
□ 进度条显示渲染进度
□ 完成后弹出提示，可选择打开输出目录
□ 输出 MP4 可播放，包含配音
□ 生成的视频包含字幕
□ BGM 正常混合
```

### 5.5 批量处理测试

```
□ 添加多个脚本到列表
□ 开始批量处理后逐条处理
□ 列表状态更新（待处理→处理中→已完成）
□ 总体进度条显示正确
□ 完成后弹出完成提示
□ 打开输出目录按钮正常工作
```

### 5.6 设置测试

```
□ 设置对话框打开正常
□ 修改分辨率/FPS/编码参数
□ 修改 BGM 音量
□ 切换 TTS 引擎/语音
□ 保存后设置持久化
□ 恢复默认功能正常
```

---

## Level 6: 性能测试

### 6.1 启动时间

```bash
python -c "
import time, os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
start = time.time()
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
from ui.main_window import MainWindow
w = MainWindow()
elapsed = time.time() - start
print(f'GUI 启动时间: {elapsed:.2f}s')
w.close(); app.quit()
"
```

### 6.2 素材扫描性能

```bash
# 在不同素材量下测试
python -c "
from core.database import Database
from core.scanner import AssetScanner
import time

db = Database('./database/perf_test.db')
db.init_tables()

for count in ['100', '500', '1000']:
    # 生成测试文件...
    start = time.time()
    scanner = AssetScanner(db, f'./tests/fixtures/perf/{count}')
    n = scanner.scan_all()
    elapsed = time.time() - start
    print(f'{n} files scanned in {elapsed:.2f}s ({n/elapsed:.0f} files/s)')

db.close()
"
```

### 6.3 渲染性能基准

| 视频长度 | 预期渲染时间 | 实际测量 |
|---|---|---|
| 15 秒 | < 2 分钟 | ______ |
| 30 秒 | < 4 分钟 | ______ |
| 1 分钟 | < 8 分钟 | ______ |
| 5 分钟 | < 40 分钟 | ______ |

### 6.4 内存使用基准

| 测试场景 | 预期峰值 | 实际测量 |
|---|---|---|
| 空窗口 | < 200 MB | ______ |
| 素材扫描(1000 文件) | < 300 MB | ______ |
| Timeline 构建 | < 200 MB | ______ |
| 渲染 1 分钟视频 | < 2 GB | ______ |

---

## 一键运行所有自动化测试

```bash
# 完整测试（单元+集成+模块导入）
tests\test_pipeline.bat
```

该批处理文件会自动执行：
1. 检查 Python / FFmpeg 环境
2. 安装缺失的 Python 依赖
3. 运行 168 个 pytest 单元测试
4. 导入验证 22 个模块
5. 测试素材扫描 + Timeline 构建
6. 尝试完整渲染管线（可选）

---

## 常见问题排查

| 问题 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| `No module named pytest` | pytest 未安装 | `pip install pytest` |
| FFmpeg 命令失败 | FFmpeg 未安装或不在 PATH | [下载 FFmpeg](https://ffmpeg.org/download.html) |
| `OSError: [WinError 6]` | Windows 句柄问题 | 重试或重启终端 |
| GUI 离线渲染失败 | 缺少 Qt 平台插件 | 确保有显示器或设置 `QT_QPA_PLATFORM=offscreen` |
| 中文乱码 | 终端编码 | 使用支持 UTF-8 的终端（Windows Terminal） |
| 素材显示为占位符 | 无匹配素材 | 运行 `generate_test_assets.bat` 生成测试素材 |

---

## 测试通过标准

| 等级 | 测试项 | 必须通过 |
|---|---|---|
| P0 | 168 个单元测试 | ✓ |
| P0 | 22 个模块导入 | ✓ |
| P1 | 素材扫描 + 搜索 | ✓ |
| P1 | Timeline 构建 + 校验 | ✓ |
| P2 | 完整管线（脚本→视频） | 建议通过 |
| P3 | GUI 启动 | ✓ |
| P3 | GUI 主要交互 | ✓ |
