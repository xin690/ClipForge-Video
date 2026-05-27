import json
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QProgressBar, QGroupBox, QFormLayout, QLineEdit,
    QSplitter, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from core.config import get_config, get, save_config
from core.models import Script, Segment
from core.ai_planner import AIPlanner
from core.downloader import Downloader

_log = logging.getLogger("ui.ai_plan")


class PlanWorker(QThread):
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, planner: AIPlanner, theme: str, style: str):
        super().__init__()
        self.planner = planner
        self.theme = theme
        self.style = style

    def run(self):
        try:
            result = self.planner.plan_from_theme(self.theme, self.style)
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class DownloadWorker(QThread):
    progress_signal = pyqtSignal(str, float)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, downloader: Downloader, queries: list, assets_dir: str, media_type: str):
        super().__init__()
        self.downloader = downloader
        self.queries = queries
        self.assets_dir = assets_dir
        self.media_type = media_type

    def run(self):
        try:
            results = self.downloader.search_and_download(
                self.queries,
                self.assets_dir,
                self.media_type,
                progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct),
            )
            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))


class AIPlanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 视频规划")
        self.resize(900, 700)
        self.setMinimumSize(800, 600)

        self._plan_result: dict | None = None
        self._script: Script | None = None
        self._search_queries: list[dict] = []
        self._plan_worker: PlanWorker | None = None
        self._download_worker: DownloadWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_label = QLabel("AI 视频规划")
        title_label.setObjectName("heading")
        layout.addWidget(title_label)

        desc = QLabel("输入主题文案，AI 将为您自动规划视频内容并搜索素材。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; margin-bottom: 4px;")
        layout.addWidget(desc)

        input_group = QGroupBox("输入")
        input_layout = QFormLayout(input_group)
        input_layout.setContentsMargins(12, 16, 12, 12)
        input_layout.setSpacing(10)

        self.theme_edit = QPlainTextEdit()
        self.theme_edit.setFont(QFont("Microsoft YaHei", 10))
        self.theme_edit.setPlaceholderText(
            "请描述您想创建的视频主题...\n\n"
            "例如：制作一个关于中国自然风光的短视频，展示高山、大海、草原的壮丽景色，"
            "配合优美的口播文案和舒缓的背景音乐。"
        )
        self.theme_edit.setMaximumHeight(120)
        input_layout.addRow("主题文案:", self.theme_edit)

        style_row = QHBoxLayout()
        self.style_combo = QComboBox()
        self.style_combo.addItems(["knowledge", "news", "entertainment", "commerce"])
        self.style_label_map = {"knowledge": "知识科普", "news": "新闻资讯", "entertainment": "娱乐", "commerce": "电商带货"}
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        self._style_desc_label = QLabel(self.style_label_map.get("knowledge", ""))
        self._style_desc_label.setStyleSheet("color: #a6adc8;")
        style_row.addWidget(self.style_combo)
        style_row.addWidget(self._style_desc_label)
        style_row.addStretch()
        input_layout.addRow("视频风格:", style_row)

        layout.addWidget(input_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.plan_btn = QPushButton("AI 规划")
        self.plan_btn.setObjectName("primary_btn")
        self.plan_btn.setMinimumWidth(120)
        self.plan_btn.setMinimumHeight(36)
        self.plan_btn.clicked.connect(self._on_plan)
        btn_layout.addWidget(self.plan_btn)

        layout.addLayout(btn_layout)

        self.preview_group = QGroupBox("规划结果预览")
        preview_layout = QVBoxLayout(self.preview_group)
        preview_layout.setContentsMargins(12, 16, 12, 12)
        preview_layout.setSpacing(8)

        self.preview_title = QLabel("点击「AI 规划」开始")
        self.preview_title.setStyleSheet("color: #a6adc8; font-size: 13px;")
        preview_layout.addWidget(self.preview_title)

        self.seg_table = QTableWidget(0, 5)
        self.seg_table.setHorizontalHeaderLabels(["ID", "文案", "关键词", "情绪", "时长(s)"])
        self.seg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.seg_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.seg_table.setMinimumHeight(200)
        self.seg_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        preview_layout.addWidget(self.seg_table)

        layout.addWidget(self.preview_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(self.status_label)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.download_btn = QPushButton("下载素材")
        self.download_btn.setMinimumWidth(120)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download)
        bottom_layout.addWidget(self.download_btn)

        self.save_btn = QPushButton("保存脚本")
        self.save_btn.setMinimumWidth(120)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)

        layout.addLayout(bottom_layout)

    def _on_style_changed(self, text: str):
        self._style_desc_label.setText(self.style_label_map.get(text, ""))

    def _on_plan(self):
        theme = self.theme_edit.toPlainText().strip()
        if not theme:
            QMessageBox.warning(self, "输入为空", "请输入视频主题文案。")
            return

        config = get_config()
        ai_cfg = config.get("ai", {})
        if not ai_cfg.get("enabled") or not ai_cfg.get("api_key"):
            reply = QMessageBox.question(
                self, "AI 未启用",
                "AI 功能未启用或 API Key 未配置。\n\n是否打开设置对话框进行配置？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                from ui.settings_dialog import SettingsDialog
                dlg = SettingsDialog(self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    pass
            return

        self._plan_result = None
        self._script = None
        self._search_queries = []

        self.plan_btn.setEnabled(False)
        self.plan_btn.setText("规划中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("正在调用 AI 规划视频内容...")
        self.download_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        self._plan_worker = PlanWorker(
            AIPlanner(config), theme, self.style_combo.currentText()
        )
        self._plan_worker.finished_signal.connect(self._on_plan_finished)
        self._plan_worker.error_signal.connect(self._on_plan_error)
        self._plan_worker.finished.connect(self._worker_cleanup)
        self._plan_worker.start()

    def _on_plan_finished(self, result):
        self.plan_btn.setEnabled(True)
        self.plan_btn.setText("AI 规划")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        if result is None:
            self.status_label.setText("AI 规划失败，请检查 API 配置或网络连接。")
            QMessageBox.warning(self, "规划失败", "AI 未能生成有效的视频脚本。\n请检查 API Key 和网络连接后重试。")
            return

        self._plan_result = result
        self._script = result.get("script")
        self._search_queries = result.get("search_queries", [])

        if self._script:
            self._display_script(self._script)
            q_count = len(self._search_queries)
            self.status_label.setText(f"规划成功！共 {len(self._script.segments)} 个分段，{q_count} 个搜索关键词。")
            self.download_btn.setEnabled(q_count > 0)
            self.save_btn.setEnabled(True)
        else:
            self.status_label.setText("规划失败：未生成有效脚本。")
            self.progress_bar.setValue(0)

    def _on_plan_error(self, error_msg: str):
        self.plan_btn.setEnabled(True)
        self.plan_btn.setText("AI 规划")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"规划出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"AI 规划失败:\n{error_msg}")

    def _display_script(self, script: Script):
        self.preview_title.setText(f"脚本标题: {script.title}  |  风格: {script.style}  |  总时长: {script.duration}s")
        self.preview_title.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: bold;")

        segs = script.segments
        self.seg_table.setRowCount(len(segs))
        for i, seg in enumerate(segs):
            self.seg_table.setItem(i, 0, QTableWidgetItem(str(seg.id)))
            self.seg_table.setItem(i, 1, QTableWidgetItem(seg.text))
            self.seg_table.setItem(i, 2, QTableWidgetItem(", ".join(seg.keywords)))
            self.seg_table.setItem(i, 3, QTableWidgetItem(seg.emotion))
            self.seg_table.setItem(i, 4, QTableWidgetItem(str(seg.duration)))

    def _on_download(self):
        if not self._search_queries:
            QMessageBox.information(self, "无搜索词", "没有可用的搜索词。")
            return

        config = get_config()
        dl_cfg = config.get("downloader", {})
        if not dl_cfg.get("api_key"):
            reply = QMessageBox.question(
                self, "素材 API 未配置",
                "Pexels/Pixabay API Key 未配置。\n\n请先到 https://www.pexels.com/api/ 免费注册获取 API Key，\n然后在设置中填入。\n\n是否打开设置对话框？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                from ui.settings_dialog import SettingsDialog
                dlg = SettingsDialog(self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    pass
            return

        self.download_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.plan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        assets_dir = get("paths.assets", "./assets")
        self._download_worker = DownloadWorker(
            Downloader(config),
            self._search_queries,
            assets_dir,
            "video",
        )
        self._download_worker.progress_signal.connect(self._on_download_progress)
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.error_signal.connect(self._on_download_error)
        self._download_worker.finished.connect(self._worker_cleanup)
        self._download_worker.start()

    def _on_download_progress(self, message: str, pct: float):
        self.status_label.setText(message)
        self.progress_bar.setValue(int(pct * 100))

    def _on_download_finished(self, results: list[str]):
        self.download_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.plan_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"素材下载完成！成功 {len(results)} 个文件。请打开软件扫描素材后即可生成视频。")

    def _on_download_error(self, error_msg: str):
        self.download_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.plan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"下载出错: {error_msg}")
        QMessageBox.critical(self, "下载错误", f"素材下载失败:\n{error_msg}")

    def _on_save(self):
        if self._script is None:
            return

        for seg in self._script.segments:
            for sq in self._search_queries:
                if sq.get("segment_id") == seg.id:
                    query = sq.get("query", "")
                    existing = set(k.lower() for k in seg.keywords)
                    for term in query.split():
                        term = term.strip(" ,.()[]{}\"'")
                        if term.lower() not in existing and len(term) > 1:
                            seg.keywords.append(term)
                            existing.add(term.lower())
                    break

        scripts_dir = get("paths.scripts", "./scripts")
        Path(scripts_dir).mkdir(parents=True, exist_ok=True)

        title_safe = self._script.title.replace("/", "_").replace("\\", "_").strip()
        filename = f"{title_safe}_{self._script.style}.json" if self._script.style else f"{title_safe}.json"
        save_path = Path(scripts_dir) / filename

        data = self._script.model_dump()
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.status_label.setText(f"脚本已保存: {save_path}")
        QMessageBox.information(self, "保存成功", f"脚本已保存到:\n{save_path}")

    def _worker_cleanup(self):
        if self._plan_worker:
            if self._plan_worker.isRunning():
                self._plan_worker.quit()
                self._plan_worker.wait(3000)
            self._plan_worker.deleteLater()
            self._plan_worker = None
        if self._download_worker:
            if self._download_worker.isRunning():
                self._download_worker.quit()
                self._download_worker.wait(3000)
            self._download_worker.deleteLater()
            self._download_worker = None
