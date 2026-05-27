import json
import os
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit,
    QLabel, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QComboBox, QLineEdit, QSpinBox,
    QGroupBox, QFormLayout, QCheckBox, QTabWidget, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor

from core.models import Script, Segment
from core.config import get
from core.pipeline import Pipeline, PipelineProgress, PipelineStep
from ui.worker import PipelineWorker


class JSONHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[str, QTextCharFormat]] = []

        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor("#89b4fa"))
        key_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append(('"([^"\\\\]|\\\\.)*"\\s*:', key_fmt))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#a6e3a1"))
        self._rules.append(('"([^"\\\\]|\\\\.)*"', string_fmt))

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#fab387"))
        self._rules.append((r"\b-?\d+\.?\d*\b", number_fmt))

        bool_fmt = QTextCharFormat()
        bool_fmt.setForeground(QColor("#cba6f7"))
        self._rules.append((r"\b(true|false|null)\b", bool_fmt))

    def highlightBlock(self, text: str):
        import re
        for pattern, fmt in self._rules:
            for match in re.finditer(pattern, text):
                start, end = match.start(), match.end()
                self.setFormat(start, end - start, fmt)


class ScriptEditorTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_file: str | None = None
        self._result_path: str | None = None
        self._worker: PipelineWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        header = QHBoxLayout()

        self.title_label = QLabel("脚本编辑器")
        self.title_label.setObjectName("heading")
        header.addWidget(self.title_label)

        header.addStretch()

        self.btn_new = QPushButton("新建")
        self.btn_new.clicked.connect(self._new_script)
        header.addWidget(self.btn_new)

        self.btn_open = QPushButton("打开")
        self.btn_open.clicked.connect(self._open_script)
        header.addWidget(self.btn_open)

        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self._save_script)
        header.addWidget(self.btn_save)

        self.btn_validate = QPushButton("验证")
        self.btn_validate.clicked.connect(self._validate_script)
        header.addWidget(self.btn_validate)

        header.addWidget(self._make_vsep())

        self.btn_generate = QPushButton("▶ 生成视频")
        self.btn_generate.setObjectName("primary_btn")
        self.btn_generate.clicked.connect(self._generate_video)
        header.addWidget(self.btn_generate)

        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        json_group = QWidget()
        json_layout = QVBoxLayout(json_group)
        json_layout.setContentsMargins(0, 0, 0, 0)
        json_label = QLabel("JSON 脚本")
        json_label.setObjectName("subheading")
        json_layout.addWidget(json_label)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setTabStopDistance(24)
        self.editor.setPlaceholderText("在此粘贴或编辑脚本 JSON...")
        self.highlighter = JSONHighlighter(self.editor.document())
        json_layout.addWidget(self.editor)

        splitter.addWidget(json_group)

        form_group = QWidget()
        form_layout = QVBoxLayout(form_group)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_label = QLabel("脚本属性")
        form_label.setObjectName("subheading")
        form_layout.addWidget(form_label)

        self.prop_widget = QWidget()
        prop_form = QFormLayout(self.prop_widget)
        self.input_title = QLineEdit("我的视频")
        prop_form.addRow("标题:", self.input_title)

        self.combo_style = QComboBox()
        self.combo_style.addItems(["knowledge", "news", "entertainment", "commerce"])
        prop_form.addRow("风格:", self.combo_style)

        self.combo_voice = QComboBox()
        self.combo_voice.addItems(["female_01", "male_01"])
        prop_form.addRow("配音:", self.combo_voice)

        self.input_bgm = QLineEdit()
        self.input_bgm.setPlaceholderText("BGM 文件名（可选）")
        prop_form.addRow("BGM:", self.input_bgm)

        form_layout.addWidget(self.prop_widget)

        seg_label = QLabel("分段列表")
        seg_label.setObjectName("subheading")
        form_layout.addWidget(seg_label)

        self.seg_table = QTableWidget(0, 5)
        self.seg_table.setHorizontalHeaderLabels(["ID", "文本", "关键词", "情绪", "时长(s)"])
        self.seg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.seg_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        form_layout.addWidget(self.seg_table)

        seg_btn_layout = QHBoxLayout()
        self.btn_add_seg = QPushButton("+ 添加分段")
        self.btn_add_seg.clicked.connect(self._add_segment)
        seg_btn_layout.addWidget(self.btn_add_seg)

        self.btn_remove_seg = QPushButton("- 删除选中")
        self.btn_remove_seg.clicked.connect(self._remove_segment)
        seg_btn_layout.addWidget(self.btn_remove_seg)

        self.btn_sync_form = QPushButton("↻ 从表单更新 JSON")
        self.btn_sync_form.clicked.connect(self._sync_form_to_json)
        seg_btn_layout.addWidget(self.btn_sync_form)

        form_layout.addLayout(seg_btn_layout)

        splitter.addWidget(form_group)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subheading")
        layout.addWidget(self.status_label)

        self._new_script()

    def load_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.setPlainText(content)
            self.current_file = path
            self.title_label.setText(f"脚本编辑器 - {Path(path).name}")
            self._sync_json_to_form()
            self.status_label.setText(f"已加载: {path}")
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _new_script(self):
        default = {
            "title": "我的视频",
            "duration": 30,
            "style": "knowledge",
            "voice": "female_01",
            "bgm": "",
            "segments": [
                {"id": 1, "text": "请输入第一段文案", "keywords": ["关键词"], "emotion": "normal", "duration": 5},
                {"id": 2, "text": "请输入第二段文案", "keywords": ["关键词"], "emotion": "strong", "duration": 6},
            ],
        }
        self.editor.setPlainText(json.dumps(default, ensure_ascii=False, indent=2))
        self.current_file = None
        self.title_label.setText("脚本编辑器 - 新建脚本")
        self._sync_json_to_form()

    def _open_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开脚本", get("paths.scripts", "./scripts"),
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            self.load_file(path)

    def _save_script(self):
        if self.current_file:
            path = self.current_file
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "保存脚本", get("paths.scripts", "./scripts"),
                "JSON 文件 (*.json)"
            )
            if not path:
                return

        try:
            content = self.editor.toPlainText()
            json.loads(content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file = path
            self.title_label.setText(f"脚本编辑器 - {Path(path).name}")
            self.status_label.setText(f"已保存: {path}")
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "保存失败", f"JSON 格式错误: {e}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def _validate_script(self):
        try:
            data = json.loads(self.editor.toPlainText())
            Script(**data)
            self.status_label.setText("✓ 脚本验证通过")
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON 格式错误", str(e))
        except Exception as e:
            QMessageBox.warning(self, "脚本验证失败", str(e))

    def _sync_json_to_form(self):
        try:
            data = json.loads(self.editor.toPlainText())
            self.input_title.setText(data.get("title", ""))
            style = data.get("style", "knowledge")
            idx = self.combo_style.findText(style)
            if idx >= 0:
                self.combo_style.setCurrentIndex(idx)
            voice = data.get("voice", "female_01")
            idx = self.combo_voice.findText(voice)
            if idx >= 0:
                self.combo_voice.setCurrentIndex(idx)
            self.input_bgm.setText(data.get("bgm", ""))

            segs = data.get("segments", [])
            self.seg_table.setRowCount(len(segs))
            for i, seg in enumerate(segs):
                self.seg_table.setItem(i, 0, QTableWidgetItem(str(seg.get("id", i + 1))))
                self.seg_table.setItem(i, 1, QTableWidgetItem(seg.get("text", "")))
                kw = seg.get("keywords", [])
                self.seg_table.setItem(i, 2, QTableWidgetItem(", ".join(kw) if isinstance(kw, list) else str(kw)))
                self.seg_table.setItem(i, 3, QTableWidgetItem(seg.get("emotion", "normal")))
                self.seg_table.setItem(i, 4, QTableWidgetItem(str(seg.get("duration", 5))))
        except (json.JSONDecodeError, Exception):
            pass

    def _sync_form_to_json(self):
        try:
            data = json.loads(self.editor.toPlainText()) if self.editor.toPlainText().strip() else {}
        except json.JSONDecodeError:
            data = {}

        data["title"] = self.input_title.text()
        data["style"] = self.combo_style.currentText()
        data["voice"] = self.combo_voice.currentText()
        data["bgm"] = self.input_bgm.text()
        data["duration"] = 0

        segments = []
        for row in range(self.seg_table.rowCount()):
            id_item = self.seg_table.item(row, 0)
            text_item = self.seg_table.item(row, 1)
            kw_item = self.seg_table.item(row, 2)
            em_item = self.seg_table.item(row, 3)
            dur_item = self.seg_table.item(row, 4)

            kw_text = kw_item.text().strip() if kw_item else ""
            keywords = [k.strip() for k in kw_text.split(",") if k.strip()]

            seg = {
                "id": int(id_item.text()) if id_item else row + 1,
                "text": text_item.text() if text_item else "",
                "keywords": keywords,
                "emotion": em_item.text() if em_item else "normal",
                "duration": int(dur_item.text()) if dur_item else 5,
            }
            segments.append(seg)
            data["duration"] += seg["duration"]

        data["segments"] = segments
        self.editor.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
        self.status_label.setText("✓ 表单已同步到 JSON")

    def _add_segment(self):
        row = self.seg_table.rowCount()
        self.seg_table.insertRow(row)
        self.seg_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.seg_table.setItem(row, 1, QTableWidgetItem(""))
        self.seg_table.setItem(row, 2, QTableWidgetItem(""))
        self.seg_table.setItem(row, 3, QTableWidgetItem("normal"))
        self.seg_table.setItem(row, 4, QTableWidgetItem("5"))

    def _remove_segment(self):
        current = self.seg_table.currentRow()
        if current >= 0:
            self.seg_table.removeRow(current)
            for i in range(self.seg_table.rowCount()):
                item = self.seg_table.item(i, 0)
                if item:
                    item.setText(str(i + 1))

    def _generate_video(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            return

        try:
            data = json.loads(self.editor.toPlainText())
            script = Script(**data)
        except Exception as e:
            QMessageBox.warning(self, "脚本无效", f"请先修复脚本错误:\n{e}")
            return

        output_dir = get("paths.output", "./output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=output_dir, encoding="utf-8"
        )
        json.dump(data, tmp, ensure_ascii=False)
        tmp_path = tmp.name
        tmp.close()

        output_name = f"{data['title']}_{data['style']}.mp4"
        output_path = os.path.join(output_dir, output_name)

        from core.config import get_config
        config = get_config()

        self.btn_generate.setText("⏹ 取消")
        self.btn_generate.setObjectName("danger_btn")
        self.setStyleSheet(self.styleSheet())
        self.main_window.show_progress(True)
        self.status_label.setText("正在生成视频...")

        self._worker = PipelineWorker(config, tmp_path, output_path)
        self._worker.finished.connect(self._on_generate_finished)
        self._worker.error.connect(self._on_generate_error)
        self._worker.progress_updated.connect(self._on_generate_progress)
        self._worker.start()

    def _on_generate_progress(self, progress: PipelineProgress):
        if progress.step == PipelineStep.RENDER_VIDEO:
            self.main_window.set_progress(int(progress.progress * 100))
            self.status_label.setText(f"渲染中 {progress.progress*100:.0f}%")
        else:
            self.status_label.setText(progress.message)

    def _on_generate_finished(self, output_path: str):
        self._reset_generate_btn()
        self.main_window.show_progress(False)
        self._result_path = output_path
        self.status_label.setText(f"✓ 视频已生成: {output_path}")
        self.main_window.play_video(output_path)

        reply = QMessageBox.question(
            self, "生成完成",
            f"视频已保存到:\n{output_path}\n\n是否打开输出目录?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.startfile(os.path.abspath(os.path.dirname(output_path)))

    def _on_generate_error(self, error_msg: str):
        self._reset_generate_btn()
        self.main_window.show_progress(False)
        self.status_label.setText(f"✗ 生成失败")
        logging.getLogger("ui").error("生成失败: %s", error_msg)
        QMessageBox.critical(self, "生成失败", error_msg)

    def _reset_generate_btn(self):
        self.btn_generate.setText("▶ 生成视频")
        self.btn_generate.setObjectName("primary_btn")
        self.setStyleSheet(self.styleSheet())
        self._worker_cleanup()

    def _worker_cleanup(self):
        if self._worker:
            if self._worker.isRunning():
                self._worker.cancel()
                self._worker.wait(3000)
            self._worker.deleteLater()
            self._worker = None

    def _make_vsep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFrameShadow(QFrame.Shadow.Sunken)
        f.setStyleSheet("color: #313244;")
        f.setMaximumWidth(2)
        return f
