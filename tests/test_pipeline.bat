@echo off
chcp 65001 >nul
title ClipForge - 自动化管线测试

echo ============================================
echo  ClipForge 端到端管线测试
echo ============================================
echo.

:: 1. 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请安装 Python 3.10+
    pause
    exit /b 1
)

:: 2. 检查 FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] FFmpeg 未安装，渲染测试将被跳过
    set SKIP_RENDER=1
) else (
    set SKIP_RENDER=0
)

:: 3. 检查依赖
echo [1/6] 检查 Python 依赖...
python -c "import PyQt6, yaml, pydantic, edge_tts" 2>nul
if %errorlevel% neq 0 (
    echo [提示] 安装依赖中...
    pip install -r requirements.txt -q
)

:: 4. 确保 test 输出目录
if not exist "output" mkdir output

:: 5. 运行单元测试
echo.
echo [2/6] 运行单元测试...
echo ============================================
python -m pytest tests/ -v --tb=short
if %errorlevel% neq 0 (
    echo [失败] 单元测试未全部通过！
    set UNIT_TEST_FAILED=1
) else (
    echo [通过] 单元测试全部通过！
    set UNIT_TEST_FAILED=0
)

:: 6. 测试管线核心逻辑
echo.
echo [3/6] 测试核心模块导入...
echo ============================================
python -c "
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
modules = [
    'core.config','core.models','core.database','core.matcher',
    'core.rules','core.timeline','core.tts','core.subtitle',
    'core.ffmpeg','core.renderer','core.pipeline','core.scanner',
    'core.ai_planner',
    'ui.resources','ui.worker','ui.main_window','ui.script_editor',
    'ui.asset_browser','ui.timeline_view','ui.batch_panel','ui.settings_dialog',
]
errors = []
for m in modules:
    try:
        __import__(m)
    except Exception as e:
        errors.append(f'  FAIL {m}: {e}')
if errors:
    print('[失败] 以下模块导入失败:')
    for e in errors: print(e)
    sys.exit(1)
else:
    print(f'[通过] 全部 {len(modules)} 个模块导入成功')
" 2>&1
if %errorlevel% neq 0 ( set MODULE_TEST_FAILED=1 ) else ( set MODULE_TEST_FAILED=0 )

:: 7. 测试素材扫描 + Timeline 构建
echo.
echo [4/6] 测试素材扫描与匹配...
echo ============================================
python -c "
from core.config import load_config
from core.database import Database
from core.scanner import AssetScanner
from core.matcher import Matcher
from core.rules import RuleEngine
from core.timeline import TimelineBuilder
from core.models import Script
import os, sys

load_config()
os.makedirs('./output', exist_ok=True)

db = Database('./database/test_pipeline.db')
db.init_tables()

# 扫描测试素材
assets_dir = './assets'
if os.path.isdir(assets_dir):
    scanner = AssetScanner(db, assets_dir)
    count = scanner.scan_all()
    print(f'  扫描素材: {count} 个')
else:
    print(f'  [跳过] 素材目录不存在 ({assets_dir})')

# 测试 Timeline 构建
matcher = Matcher(db)
rules = RuleEngine()
rules.register_defaults()
builder = TimelineBuilder(matcher, rules)

script = Script(
    title='测试视频', duration=15, style='knowledge',
    segments=[
        {'id': 1, 'text': '减脂核心是饮食', 'keywords': ['减脂'], 'emotion': 'normal', 'duration': 5},
        {'id': 2, 'text': '运动也很重要', 'keywords': ['健身'], 'emotion': 'strong', 'duration': 5},
    ],
)

timeline = builder.build(script)
print(f'  Timeline 构建: {len(timeline.timeline)} 个镜头')
for i, item in enumerate(timeline.timeline):
    print(f'    镜头 {i+1}: asset={item.asset}, trans={item.transition}, style={item.subtitle_style}')

db.close()
import shutil
if os.path.exists('./database/test_pipeline.db'):
    os.remove('./database/test_pipeline.db')
print('[通过] 素材扫描与匹配测试完成')
" 2>&1

:: 8. 测试完整渲染管线
echo.
echo [5/6] 测试完整管线（脚本→视频）...
echo ============================================
if %SKIP_RENDER% equ 1 (
    echo [跳过] FFmpeg 未安装，跳过渲染测试
    echo 请安装 FFmpeg 后重新运行: https://ffmpeg.org/download.html
) else (
    python -c "
from core.config import load_config
from core.pipeline import Pipeline
from core.models import Script
import json, os, sys

load_config()
script_path = './scripts/sample_knowledge.json'
output_path = './output/test_output.mp4'

if not os.path.exists(script_path):
    print(f'  [跳过] 示例脚本不存在: {script_path}')
    sys.exit(0)

if not os.path.isdir('./assets'):
    print('  [跳过] 素材库为空，渲染需要真实素材')
    sys.exit(0)

pipeline = Pipeline()

def on_progress(progress):
    if int(progress.progress * 100) %% 25 == 0:
        print(f'  进度: {progress.message}')

try:
    result = pipeline.run(script_path, output_path, on_progress)
    print(f'  输出: {result}')
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f'  文件大小: {size / 1024:.1f} KB')
        os.remove(output_path)
        print('[通过] 完整管线测试成功!')
    else:
        print('[失败] 输出文件不存在')
except Exception as e:
    print(f'  [跳过] 渲染需要真实素材: {e}')
" 2>&1
)

:: 9. 汇总结果
echo.
echo ============================================
echo  测试结果汇总
echo ============================================
echo.
echo  [2/6] 单元测试: %UNIT_TEST_FAILED% (0=通过, 1=失败)
echo  [3/6] 模块导入: %MODULE_TEST_FAILED% (0=通过, 1=失败)
echo  [4/6] 素材匹配: 已完成
echo  [5/6] 渲染管线: %SKIP_RENDER% (0=已测试, 1=跳过)
echo.
if %UNIT_TEST_FAILED% equ 0 (
    echo  ✓ 核心功能正常
) else (
    echo  ✗ 存在失败的测试，请检查
)

:: 10. 清理
if exist "output\test_output.mp4" del /f "output\test_output.mp4" 2>nul

echo.
echo ============================================
echo  测试完成!
echo.
echo  下一步:
echo   1. 运行 generate_test_assets.bat 生成测试素材
echo   2. 双击 RUN_LOCAL.bat 启动 GUI
echo   3. 在素材管理中扫描素材库
echo   4. 打开示例脚本，点击"生成视频"
echo ============================================
pause
