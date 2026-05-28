import json
import time
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QProgressBar, QGroupBox, QFormLayout, QSpinBox,
    QSplitter, QWidget, QTabWidget, QTextBrowser,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush

from core.config import get_config, get
from core.models import Script
from core.ai_planner import AIPlanner, CachedPlanner
from core.downloader import Downloader
from core.tts import preview_duration
from core.qa import QAChecker, QASummary

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


class V2PlanWorker(QThread):
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, planner: AIPlanner, theme: str, style: str, target_duration: int = 0):
        super().__init__()
        self.planner = planner
        self.theme = theme
        self.style = style
        self.target_duration = target_duration

    def run(self):
        try:
            result = self.planner.plan_from_theme_v2(self.theme, self.style, target_duration=self.target_duration)
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
        self.resize(900, 780)
        self.setMinimumSize(800, 680)

        self._plan_result: dict | None = None
        self._script: Script | None = None
        self._search_queries: list[dict] = []
        self._versions: list[dict] = []
        self._tts_durations: list[float] = []
        self._plan_worker: QThread | None = None
        self._download_worker: DownloadWorker | None = None
        self._last_plan_click: float = 0
        self._editing = False
        self._qa_summary: QASummary | None = None

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

        time_row = QHBoxLayout()
        self.target_duration_spin = QSpinBox()
        self.target_duration_spin.setRange(0, 3600)
        self.target_duration_spin.setValue(0)
        self.target_duration_spin.setSuffix(" 秒")
        self.target_duration_spin.setSingleStep(10)
        self.target_duration_spin.setSpecialValueText("不限制")
        self.target_duration_spin.setFixedWidth(180)
        time_row.addWidget(self.target_duration_spin)
        time_row.addWidget(QLabel("（0=不限制，步长10秒，最长3600秒）"))
        time_row.addStretch()
        input_layout.addRow("目标时长:", time_row)

        layout.addWidget(input_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.optimize_btn = QPushButton("优化提示词")
        self.optimize_btn.setMinimumWidth(100)
        self.optimize_btn.setMinimumHeight(36)
        self.optimize_btn.clicked.connect(self._on_optimize_theme)
        btn_layout.addWidget(self.optimize_btn)

        self.plan_btn = QPushButton("AI 规划")
        self.plan_btn.setObjectName("primary_btn")
        self.plan_btn.setMinimumWidth(120)
        self.plan_btn.setMinimumHeight(36)
        self.plan_btn.clicked.connect(self._on_plan)
        btn_layout.addWidget(self.plan_btn)

        layout.addLayout(btn_layout)

        self.result_tabs = QTabWidget()
        self.result_tabs.addTab(self._setup_script_tab(), "脚本编辑")
        self.result_tabs.addTab(self._setup_preview_tab(), "脚本预览")
        self.result_tabs.addTab(self._setup_qa_tab(), "内容检查")
        self.result_tabs.setVisible(False)
        layout.addWidget(self.result_tabs, 1)

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

    def _setup_script_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.preview_title = QLabel("点击「AI 规划」开始")
        self.preview_title.setStyleSheet("color: #a6adc8; font-size: 13px;")
        layout.addWidget(self.preview_title)

        toolbar = QHBoxLayout()
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(120)
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        self.version_combo.setVisible(False)
        toolbar.addWidget(QLabel("版本:"))
        toolbar.addWidget(self.version_combo)

        self.version_compare_btn = QPushButton("版本对比")
        self.version_compare_btn.setEnabled(False)
        self.version_compare_btn.clicked.connect(self._on_version_compare)
        toolbar.addWidget(self.version_compare_btn)

        self.refine_btn = QPushButton("润色该段")
        self.refine_btn.setEnabled(False)
        self.refine_btn.clicked.connect(self._on_refine_segment)
        toolbar.addWidget(self.refine_btn)

        self.replan_btn = QPushButton("重新规划")
        self.replan_btn.setEnabled(False)
        self.replan_btn.clicked.connect(self._on_replan)
        toolbar.addWidget(self.replan_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.seg_table = QTableWidget(0, 7)
        self.seg_table.setHorizontalHeaderLabels(["ID", "文案", "关键词", "情绪", "原始时长", "配音时长", "差异"])
        self.seg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.seg_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.seg_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.seg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.seg_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.seg_table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.seg_table, 1)

        return tab

    def _setup_preview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.script_preview = QTextBrowser()
        self.script_preview.setReadOnly(True)
        self.script_preview.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-size: 13px;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.script_preview, 1)

        return tab

    def _setup_qa_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.qa_summary_label = QLabel("点击「AI 规划」生成脚本后自动检查")
        self.qa_summary_label.setStyleSheet("color: #a6adc8; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.qa_summary_label)

        self.qa_table = QTableWidget(0, 4)
        self.qa_table.setHorizontalHeaderLabels(["检查项", "状态", "说明", "段落"])
        self.qa_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.qa_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.qa_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.qa_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.qa_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.qa_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.qa_table.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.qa_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.qa_table, 1)

        self.qa_rerun_btn = QPushButton("重新检查")
        self.qa_rerun_btn.setEnabled(False)
        self.qa_rerun_btn.clicked.connect(self._run_qa_check)
        layout.addWidget(self.qa_rerun_btn)

        return tab

    def _run_qa_check(self):
        if not self._script:
            return
        config = get_config()
        checker = QAChecker(config)
        summary = checker.check(self._script)
        self._qa_summary = summary
        self._populate_qa_table(summary)

    def _populate_qa_table(self, summary: QASummary):
        self.qa_table.setRowCount(0)
        status_map = {"pass": "✅ 通过", "warn": "⚠️ 警告", "fail": "❌ 失败"}
        color_map = {"pass": "#a6e3a1", "warn": "#f9e2af", "fail": "#f38ba8"}
        for r in summary.results:
            row = self.qa_table.rowCount()
            self.qa_table.insertRow(row)
            self.qa_table.setItem(row, 0, QTableWidgetItem(r.name))
            status_text = status_map.get(r.status, r.status)
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QBrush(QColor(color_map.get(r.status, "#cdd6f4"))))
            self.qa_table.setItem(row, 1, status_item)
            self.qa_table.setItem(row, 2, QTableWidgetItem(r.message))
            self.qa_table.setItem(row, 3, QTableWidgetItem(str(r.segment_id) if r.segment_id else ""))
        self.qa_summary_label.setText(
            f"质检结果: 通过 {summary.passed}/{summary.total}  "
            + (f"警告 {summary.warnings}  " if summary.warnings else "")
            + (f"失败 {summary.failures}" if summary.failures else "")
        )

    def _on_style_changed(self, text: str):
        self._style_desc_label.setText(self.style_label_map.get(text, ""))

    def _on_plan(self):
        # L5: 防抖
        now = time.time()
        if now - self._last_plan_click < 3.0:
            self.status_label.setText("操作过于频繁，请稍候...")
            return
        self._last_plan_click = now

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
        self._versions = []
        self._tts_durations = []

        self.plan_btn.setEnabled(False)
        self.plan_btn.setText("规划中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("正在调用 AI 规划视频内容...")
        self.download_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.refine_btn.setEnabled(False)
        self.replan_btn.setEnabled(False)
        self.version_combo.setVisible(False)
        self.result_tabs.setVisible(False)

        planner = AIPlanner(config)
        target_dur = self.target_duration_spin.value()
        self._plan_worker = V2PlanWorker(
            planner, theme, self.style_combo.currentText(), target_duration=target_dur
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
        self._versions = result.get("versions", [])

        if self._script:
            self._estimate_tts_durations()
            self._display_script(self._script)
            self._update_version_selector()
            self._run_qa_check()

            q_count = len(self._search_queries)
            status = f"规划成功！共 {len(self._script.segments)} 个分段，{q_count} 个搜索关键词。"
            self.status_label.setText(status)
            self.result_tabs.setVisible(True)
            self.result_tabs.setCurrentIndex(0)
            self.download_btn.setEnabled(q_count > 0)
            self.save_btn.setEnabled(True)
            self.refine_btn.setEnabled(True)
            self.replan_btn.setEnabled(True)
            self.qa_rerun_btn.setEnabled(True)
        else:
            self.status_label.setText("规划失败：未生成有效脚本。")
            self.progress_bar.setValue(0)

    def _on_plan_error(self, error_msg: str):
        self.plan_btn.setEnabled(True)
        self.plan_btn.setText("AI 规划")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"规划出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"AI 规划失败:\n{error_msg}")

    def _on_optimize_theme(self):
        theme = self.theme_edit.toPlainText().strip()
        if not theme:
            QMessageBox.warning(self, "输入为空", "请先输入视频主题文案。")
            return

        config = get_config()
        ai_cfg = config.get("ai", {})
        if not ai_cfg.get("enabled") or not ai_cfg.get("api_key"):
            QMessageBox.warning(self, "AI 未启用", "请先启用 AI 功能并配置 API Key。")
            return

        self.optimize_btn.setEnabled(False)
        self.plan_btn.setEnabled(False)
        self.status_label.setText("正在优化提示词...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        planner = AIPlanner(config)
        try:
            optimized = planner.optimize_theme(theme, self.style_combo.currentText())
            if optimized and optimized != theme:
                self.theme_edit.setPlainText(optimized)
                self.status_label.setText("提示词已优化，请检查后点击「AI 规划」。")
            else:
                self.status_label.setText("优化未产生变化，可直接使用当前提示词。")
        except Exception as e:
            self.status_label.setText(f"优化失败: {e}")
            QMessageBox.warning(self, "优化失败", str(e))
        finally:
            self.optimize_btn.setEnabled(True)
            self.plan_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

    def _show_script_preview(self):
        if not self._script:
            return
        sq_map: dict[int, str] = {}
        for sq in self._search_queries:
            sq_map[sq.get("segment_id", 0)] = sq.get("query", "")
        text = f"<h2>{self._script.title}</h2>"
        text += f"<p><b>风格:</b> {self._script.style} &nbsp;|&nbsp; <b>总时长:</b> {self._script.duration}s"
        text += f" &nbsp;|&nbsp; <b>配音:</b> {self._script.voice} &nbsp;|&nbsp; <b>BGM:</b> {self._script.bgm or '(无)'}</p>"
        text += "<hr>"
        for seg in self._script.segments:
            query = sq_map.get(seg.id, ", ".join(seg.keywords))
            text += f"<h3>段{seg.id}</h3>"
            text += f"<p>{seg.text}</p>"
            text += f"<p style='color: #89b4fa;'>关键词: {', '.join(seg.keywords)}</p>"
            text += f"<p style='color: #a6e3a1;'>情绪: {seg.emotion} &nbsp;|&nbsp; 时长: {seg.duration}s &nbsp;|&nbsp; 搜索词: {query}</p>"
            text += "<hr>"
        self.script_preview.setHtml(text)

    def _display_script(self, script: Script):
        self._editing = True
        self._show_script_preview()
        voice_desc = {"zh-CN-XiaoxiaoNeural": "Xiaoxiao(温暖女声)", "zh-CN-YunxiNeural": "Yunxi(沉稳男声)",
                       "zh-CN-XiaoyiNeural": "Xiaoyi(活泼女声)", "zh-CN-YunyangNeural": "Yunyang(激昂男声)",
                       "zh-CN-YunjianNeural": "Yunjian(专业男声)"}.get(script.voice, script.voice)
        bgm_text = f"BGM: {script.bgm}" if script.bgm else "BGM: (无)"
        self.preview_title.setText(f"脚本标题: {script.title}  |  风格: {script.style}  |  总时长: {script.duration}s  |  配音: {voice_desc}  |  {bgm_text}")
        self.preview_title.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: bold;")

        segs = script.segments
        self.seg_table.setRowCount(len(segs))
        for i, seg in enumerate(segs):
            self.seg_table.setItem(i, 0, QTableWidgetItem(str(seg.id)))
            self.seg_table.setItem(i, 1, QTableWidgetItem(seg.text))
            self.seg_table.setItem(i, 2, QTableWidgetItem(", ".join(seg.keywords)))
            self.seg_table.setItem(i, 3, QTableWidgetItem(seg.emotion))
            # 原始时长
            self.seg_table.setItem(i, 4, QTableWidgetItem(str(seg.duration)))
            # 配音时长
            if i < len(self._tts_durations):
                tts_dur = self._tts_durations[i]
                item_tts = QTableWidgetItem(f"{tts_dur:.1f}s")
                diff = tts_dur - seg.duration
                if abs(diff) > 1.0:
                    color = QColor("#ff4444") if diff > 0 else QColor("#44ff44")
                    item_tts.setForeground(QBrush(color))
                self.seg_table.setItem(i, 5, item_tts)
                diff_item = QTableWidgetItem(f"{diff:+.1f}s")
                if abs(diff) > 1.0:
                    diff_item.setForeground(QBrush(QColor("#ff4444") if diff > 0 else QColor("#44ff44")))
                self.seg_table.setItem(i, 6, diff_item)
            else:
                self.seg_table.setItem(i, 5, QTableWidgetItem("-"))
                self.seg_table.setItem(i, 6, QTableWidgetItem("-"))
        self._editing = False

    def _on_cell_changed(self, row: int, col: int):
        if self._editing or not self._script:
            return
        segs = self._script.segments
        if row >= len(segs):
            return
        seg = segs[row]
        item = self.seg_table.item(row, col)
        if not item:
            return
        new_val = item.text().strip()
        if col == 1:
            seg.text = new_val
        elif col == 2:
            seg.keywords = [k.strip() for k in new_val.split(",") if k.strip()]
        elif col == 3:
            if new_val in ("normal", "strong", "happy", "sad", "calm"):
                seg.emotion = new_val
        elif col == 4:
            try:
                seg.duration = max(2, min(15, int(float(new_val))))
            except ValueError:
                pass
        self._editing = True
        item.setText(str(seg.duration) if col == 4 else item.text())
        self._editing = False

    def _update_version_selector(self):
        if len(self._versions) > 1:
            self.version_combo.setVisible(True)
            self.version_compare_btn.setEnabled(True)
            self.version_combo.blockSignals(True)
            self.version_combo.clear()
            for idx, v in enumerate(self._versions):
                label = f"v{idx + 1}"
                c = v.get("critiques", [])
                if c:
                    label += f" ({len(c)}问题)"
                self.version_combo.addItem(label)
            self.version_combo.setCurrentIndex(len(self._versions) - 1)
            self.version_combo.blockSignals(False)

    def _on_version_changed(self, idx: int):
        if not self._versions or idx < 0 or idx >= len(self._versions):
            return
        v = self._versions[idx]
        script_dict = v.get("script", {})
        if not script_dict:
            return
        segs = script_dict.get("segments", [])
        self._editing = True
        self.seg_table.setRowCount(len(segs))
        for i, seg in enumerate(segs):
            self.seg_table.setItem(i, 0, QTableWidgetItem(str(seg.get("id", i + 1))))
            self.seg_table.setItem(i, 1, QTableWidgetItem(str(seg.get("text", ""))))
            self.seg_table.setItem(i, 2, QTableWidgetItem(", ".join(seg.get("keywords", []))))
            self.seg_table.setItem(i, 3, QTableWidgetItem(seg.get("emotion", "normal")))
            self.seg_table.setItem(i, 4, QTableWidgetItem(str(seg.get("duration", 5))))
            self.seg_table.setItem(i, 5, QTableWidgetItem("-"))
            self.seg_table.setItem(i, 6, QTableWidgetItem("-"))
        self._editing = False
        critiques = v.get("critiques", [])
        if critiques:
            self.status_label.setText(f"版本 {idx + 1} 评审意见: {'; '.join(critiques[:2])}")
        else:
            self.status_label.setText(f"版本 {idx + 1}（无问题）")

    def _on_version_compare(self):
        if len(self._versions) < 2:
            return
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QSplitter
        dlg = QDialog(self)
        dlg.setWindowTitle("版本对比")
        dlg.resize(900, 500)
        layout = QVBoxLayout(dlg)
        splitter = QSplitter()
        v1_text = QTextEdit()
        v1_text.setReadOnly(True)
        v2_text = QTextEdit()
        v2_text.setReadOnly(True)
        splitter.addWidget(v1_text)
        splitter.addWidget(v2_text)
        layout.addWidget(splitter, 1)
        import json
        if len(self._versions) >= 2:
            v1_text.setPlainText(json.dumps(self._versions[-2].get("script", {}), ensure_ascii=False, indent=2))
            v2_text.setPlainText(json.dumps(self._versions[-1].get("script", {}), ensure_ascii=False, indent=2))
        dlg.exec()

    def _estimate_tts_durations(self):
        if not self._script:
            return
        self._tts_durations = []
        voice = self._script.voice or "zh-CN-XiaoxiaoNeural"
        for seg in self._script.segments:
            try:
                d = preview_duration(seg.text, voice)
                self._tts_durations.append(d)
            except Exception:
                self._tts_durations.append(float(seg.duration))

    def _on_refine_segment(self):
        row = self.seg_table.currentRow()
        if row < 0 or not self._script:
            QMessageBox.information(self, "提示", "请先选中要润色的段落。")
            return
        seg = self._script.segments[row]
        if len(seg.text) < 5 or len(seg.text) > 200:
            QMessageBox.information(self, "提示", "文案长度需 5~200 字才可润色。")
            return

        config = get_config()
        planner = AIPlanner(config)
        if not planner.enabled:
            QMessageBox.warning(self, "AI 未启用", "请先启用 AI 功能。")
            return

        self.status_label.setText(f"正在润色段{seg.id}...")
        new_text = planner._api_optimize(seg.text)
        if new_text and new_text != seg.text:
            seg.text = new_text
            self._editing = True
            self.seg_table.setItem(row, 1, QTableWidgetItem(new_text))
            self._editing = False
            self.status_label.setText(f"段{seg.id} 文案已润色。")
        else:
            self.status_label.setText("润色未产生变化。")

    def _on_replan(self):
        reply = QMessageBox.question(
            self, "重新规划",
            "将丢弃当前结果并重新规划。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return
        CachedPlanner.invalidate_all()
        self._on_plan()

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
        self.refine_btn.setEnabled(bool(self._script))
        self.replan_btn.setEnabled(bool(self._script))
        self.progress_bar.setValue(100)
        self.status_label.setText(f"素材下载完成！成功 {len(results)} 个文件。请打开软件扫描素材后即可生成视频。")

    def _on_download_error(self, error_msg: str):
        self.download_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.plan_btn.setEnabled(True)
        self.refine_btn.setEnabled(bool(self._script))
        self.replan_btn.setEnabled(bool(self._script))
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
        if self._plan_worker and isinstance(self._plan_worker, QThread):
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
