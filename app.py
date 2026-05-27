import sys
import os
import traceback
import logging

from core.config import load_config, get
from core.ffmpeg import check_ffmpeg as _check_ffmpeg_binary


def excepthook(exc_type, exc_value, exc_tb):
    logging.getLogger("clipforge").error(
        "未捕获的异常:\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )


def check_ffmpeg() -> bool:
    available = _check_ffmpeg_binary()
    if not available:
        print("=" * 50)
        print("  警告: 未检测到 FFmpeg")
        print("  FFmpeg 是视频渲染的核心引擎")
        print("  请从 https://ffmpeg.org/download.html 下载")
        print("  并将 ffmpeg.exe 所在目录加入系统 PATH")
        print("=" * 50)
    return available


def setup_logging():
    log_level = get("logging.level", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    load_config()
    setup_logging()
    logger = logging.getLogger("clipforge")

    logger.info(f"ClipForge v{get('app.version', '0.1.0')} 启动中...")
    sys.excepthook = excepthook
    check_ffmpeg()

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print("错误: PyQt6 未安装。请执行: pip install PyQt6")
        input("按 Enter 键退出...")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("ClipForge")
    app.setApplicationDisplayName(f"ClipForge v{get('app.version', '0.1.0')}")

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    logger.info("主窗口已显示")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
