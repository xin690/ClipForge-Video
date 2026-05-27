import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QLabel, QProgressBar,
    QMenuBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from ui.resources import get_style
from ui.script_editor import ScriptEditorTab
from ui.asset_browser import AssetBrowserTab
from ui.timeline_view import TimelinePreviewWidget
from ui.preview_panel import PreviewPanel
from ui.batch_panel import BatchPanelTab
from ui.settings_dialog import SettingsDialog
from core.config import get, save_config
from core.database import Database
from core.scanner import AssetScanner


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ClipForge - AI 视频剪辑引擎 v{get('app.version', '0.1.0')}")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(get_style())

        self.db = Database(get("paths.database", "./database/clipforge.db"))
        self.db.init_tables()

        self._setup_menu()
        self._setup_tabs()
        self._setup_status_bar()
        self._check_first_run()

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        self._act_import_script = QAction("导入脚本...", self)
        self._act_import_script.triggered.connect(self._import_script)
        file_menu.addAction(self._act_import_script)

        self._act_import_assets = QAction("导入素材...", self)
        self._act_import_assets.triggered.connect(self._import_assets)
        file_menu.addAction(self._act_import_assets)

        file_menu.addSeparator()
        self._act_exit = QAction("退出", self)
        self._act_exit.triggered.connect(self.close)
        file_menu.addAction(self._act_exit)

        tool_menu = menubar.addMenu("工具(&T)")
        self._act_scan = QAction("扫描素材库", self)
        self._act_scan.triggered.connect(self._scan_assets)
        self._act_scan.setShortcut(QKeySequence("Ctrl+Shift+S"))
        tool_menu.addAction(self._act_scan)

        tool_menu.addSeparator()
        self._act_generate = QAction("生成视频", self)
        self._act_generate.setShortcut(QKeySequence("Ctrl+R"))
        tool_menu.addAction(self._act_generate)

        settings_menu = menubar.addMenu("设置(&S)")
        self._act_settings = QAction("偏好设置...", self)
        self._act_settings.triggered.connect(self._open_settings)
        settings_menu.addAction(self._act_settings)

        help_menu = menubar.addMenu("帮助(&H)")
        self._act_about = QAction("关于 ClipForge", self)
        self._act_about.triggered.connect(self._show_about)
        help_menu.addAction(self._act_about)

    def play_video(self, path: str):
        self.preview_panel.play(path)
        self.tabs.setCurrentWidget(self.preview_panel)

    def stop_playback(self):
        self.preview_panel.stop()

    def _setup_tabs(self):
        self.tabs = QTabWidget()
        self.script_editor = ScriptEditorTab(self)
        self.asset_browser = AssetBrowserTab(self)
        self.timeline_preview = TimelinePreviewWidget()
        self.preview_panel = PreviewPanel()
        self.batch_panel = BatchPanelTab(self)

        self.tabs.addTab(self.script_editor, "脚本编辑")
        self.tabs.addTab(self.asset_browser, "素材管理")
        self.tabs.addTab(self.timeline_preview, "时间轴")
        self.tabs.addTab(self.preview_panel, "预览")
        self.tabs.addTab(self.batch_panel, "批量处理")

        self.setCentralWidget(self.tabs)

        self.script_editor._on_timeline_ready = self._show_timeline

    def _show_timeline(self, timeline):
        self.timeline_preview.set_timeline(timeline)
        self.tabs.setCurrentWidget(self.timeline_preview)

    def _setup_status_bar(self):
        status = QStatusBar()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #6c7086;")
        status.addWidget(self.status_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setVisible(False)
        status.addPermanentWidget(self.progress_bar)

        self.asset_count_label = QLabel("素材: -")
        self.asset_count_label.setStyleSheet("color: #6c7086; padding: 0 8px;")
        status.addPermanentWidget(self.asset_count_label)

        self.setStatusBar(status)

    def _check_first_run(self):
        count = self.db.get_asset_count()
        self.asset_count_label.setText(f"素材: {count.get('total', 0)}")
        if count.get("total", 0) == 0:
            self.status_label.setText("提示: 素材库为空，请先导入素材或扫描素材库目录")

    def update_status(self, message: str):
        self.status_label.setText(message)

    def update_asset_count(self):
        count = self.db.get_asset_count()
        self.asset_count_label.setText(f"素材: {count.get('total', 0)}")

    def show_progress(self, visible: bool = True):
        self.progress_bar.setVisible(visible)
        self.progress_bar.setValue(0)

    def set_progress(self, value: int):
        self.progress_bar.setValue(value)

    def _import_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入脚本", get("paths.scripts", "./scripts"),
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            self.script_editor.load_file(path)
            self.tabs.setCurrentWidget(self.script_editor)

    def _import_assets(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择素材目录", get("paths.assets", "./assets")
        )
        if dir_path:
            self._run_scan(dir_path)

    def _scan_assets(self):
        self._run_scan(get("paths.assets", "./assets"))

    def _run_scan(self, assets_dir: str):
        self.show_progress(True)
        self.status_label.setText("正在扫描素材...")
        QTimer.singleShot(100, lambda: self._do_scan(assets_dir))

    def _do_scan(self, assets_dir: str):
        try:
            scanner = AssetScanner(self.db, assets_dir)
            count = scanner.scan_all()
            deleted = scanner.remove_deleted()
            self.update_asset_count()
            self.asset_browser.refresh()
            msg = f"扫描完成: 新增 {count} 个素材"
            if deleted > 0:
                msg += f"，清理 {deleted} 个失效素材"
            self.status_label.setText(msg)
        except Exception as e:
            self.status_label.setText(f"扫描出错: {e}")
        finally:
            self.show_progress(False)

    def _open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.status_label.setText("设置已保存")

    def _show_about(self):
        QMessageBox.about(
            self, "关于 ClipForge",
            f"<h3>ClipForge v{get('app.version', '0.1.0')}</h3>"
            "<p>轻量级 AI 视频创作系统</p>"
            "<p>本地优先 · 低资源 · 自动化视频生产</p>"
            "<hr>"
            "<p>技术栈: Python + PyQt6 + FFmpeg</p>"
        )

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)
