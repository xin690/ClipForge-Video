@echo off
chcp 65001 >nul
title ClipForge - 测试素材生成工具

echo ============================================
echo  ClipForge 测试素材生成器
echo ============================================
echo.
echo 使用 FFmpeg 生成测试用的视频、图片和音频素材
echo.

:: 检查 FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 FFmpeg，请先安装并加入 PATH
    pause
    exit /b 1
)

set ASSETS_DIR=assets

:: 创建素材目录
echo [1/6] 创建目录结构...
mkdir "%ASSETS_DIR%\videos" 2>nul
mkdir "%ASSETS_DIR%\images" 2>nul
mkdir "%ASSETS_DIR%\bgm" 2>nul
mkdir "%ASSETS_DIR%\voice" 2>nul

:: 生成测试视频素材
echo [2/6] 生成测试视频素材...

set VIDEOS=%ASSETS_DIR%\videos

:: 知识类素材
echo   - 生成知识类视频...
ffmpeg -y -f lavfi -i "color=c=blue:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\knowledge_01.mp4" -loglevel error
ffmpeg -y -f lavfi -i "color=c=lightblue:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\knowledge_02.mp4" -loglevel error
ffmpeg -y -f lavfi -i "color=c=darkblue:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\knowledge_03.mp4" -loglevel error

:: 健身/运动类素材
echo   - 生成运动类视频...
ffmpeg -y -f lavfi -i "color=c=green:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\fitness_01.mp4" -loglevel error
ffmpeg -y -f lavfi -i "color=c=darkgreen:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\fitness_02.mp4" -loglevel error

:: 饮食/食物类素材
echo   - 生成饮食类视频...
ffmpeg -y -f lavfi -i "color=c=orange:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\food_01.mp4" -loglevel error
ffmpeg -y -f lavfi -i "color=c=yellow:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\food_02.mp4" -loglevel error

:: 科技/商业类素材
echo   - 生成科技类视频...
ffmpeg -y -f lavfi -i "color=c=purple:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\tech_01.mp4" -loglevel error
ffmpeg -y -f lavfi -i "color=c=red:s=1920x1080:d=10:r=30" -f lavfi -i "anullsrc=r=44100:cl=mono" -c:v libx264 -preset ultrafast -crf 28 -shortest "%VIDEOS%\business_01.mp4" -loglevel error

:: 背景音乐素材
echo [3/6] 生成测试背景音乐...
set BGM=%ASSETS_DIR%\bgm

ffmpeg -y -f lavfi -i "sine=frequency=440:duration=30" -acodec libmp3lame -b:a 128k "%BGM%\bgm_knowledge.mp3" -loglevel error
ffmpeg -y -f lavfi -i "sine=frequency=523:duration=30" -acodec libmp3lame -b:a 128k "%BGM%\bgm_news.mp3" -loglevel error
ffmpeg -y -f lavfi -i "sine=frequency=659:duration=30" -acodec libmp3lame -b:a 128k "%BGM%\bgm_upbeat.mp3" -loglevel error
ffmpeg -y -f lavfi -i "sine=frequency=392:duration=30" -acodec libmp3lame -b:a 128k "%BGM%\bgm_commerce.mp3" -loglevel error

:: 验证生成结果
echo [4/6] 验证生成结果...
set VIDEO_COUNT=0
for %%f in ("%VIDEOS%\*.mp4") do set /a VIDEO_COUNT+=1
set BGM_COUNT=0
for %%f in ("%BGM%\*.mp3") do set /a BGM_COUNT+=1

echo.
echo ============================================
echo  生成完成!
echo ============================================
echo  视频素材: %VIDEO_COUNT% 个
echo  背景音乐: %BGM_COUNT% 个
echo.
echo  素材目录: %ASSETS_DIR%
echo.
echo  下一步: 运行 ClipForge，在"素材管理"Tab中点击"扫描素材库"
echo  即可将测试素材导入数据库。
echo ============================================

pause
