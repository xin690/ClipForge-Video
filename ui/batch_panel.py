import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt

from core.config import get
from core.pipeline import PipelineProgress, PipelineStep
from ui.worker import BatchWorker


class BatchPanelTab(QWidget):
    STATUS_PENDING = "待处理"
    STATUS_RUNNING = "处理中"
    STATUS_DONE = "已完成"
    STATUS_ERROR = "失败"

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._worker: BatchWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        header = QHBoxLayout()
        title = QLabel("批量处理")
        title.setObjectName("heading")
        header.addWidget(title)
        header.addStretch()

        self.btn_add = QPushButton("添加脚本")
        self.btn_add.clicked.connect(self._add_scripts)
        header.addWidget(self.btn_add)

        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self._clear_list)
        header.addWidget(self.btn_clear)

        self.output_dir_label = QLabel(f"输出: {get('paths.output', './output')}")
        self.output_dir_label.setObjectName("subheading")
        header.addWidget(self.output_dir_label)

        self.btn_output = QPushButton("浏览...")
        self.btn_output.clicked.connect(self._choose_output)
        header.addWidget(self.btn_output)

        layout.addLayout(header)

        self.script_list = QListWidget()
        self.script_list.setAlternatingRowColors(True)
        self.script_list.setStyleSheet("alternate-background-color: #181825;")
        layout.addWidget(self.script_list, 1)

        controls = QHBoxLayout()
        self.btn_start = QPushButton("▶ 开始批量处理")
        self.btn_start.setObjectName("primary_btn")
        self.btn_start.clicked.connect(self._start_batch)
        controls.addWidget(self.btn_start)

        self.btn_open_output = QPushButton("打开输出目录")
        self.btn_open_output.clicked.connect(self._open_output)
        controls.addWidget(self.btn_open_output)

        layout.addLayout(controls)

        progress_group = QWidget()
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(0, 8, 0, 0)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("subheading")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

    def _add_scripts(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择脚本文件", get("paths.scripts", "./scripts"),
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        for f in files:
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setData(Qt.ItemDataRole.UserRole + 1, self.STATUS_PENDING)
            self.script_list.addItem(item)

        self._update_start_button()

    def _clear_list(self):
        self.script_list.clear()
        self._update_start_button()

    def _choose_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", get("paths.output", "./output")
        )
        if dir_path:
            self.output_dir_label.setText(f"输出: {dir_path}")

    def _start_batch(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            return

        script_paths = []
        for i in range(self.script_list.count()):
            item = self.script_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            script_paths.append(path)
            item.setData(Qt.ItemDataRole.UserRole + 1, self.STATUS_PENDING)
            item.setText(os.path.basename(path))

        if not script_paths:
            QMessageBox.information(self, "提示", "请先添加脚本文件")
            return

        output_dir_text = self.output_dir_label.text().replace("输出: ", "")
        Path(output_dir_text).mkdir(parents=True, exist_ok=True)

        self.btn_start.setText("⏹ 取消")
        self.btn_start.setObjectName("danger_btn")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.style().unpolish(self.btn_start)
        self.style().polish(self.btn_start)

        from core.config import get_config
        self._worker = BatchWorker(get_config(), script_paths, output_dir_text)
        self._worker.progress_updated.connect(self._on_batch_progress)
        self._worker.item_finished.connect(self._on_item_finished)
        self._worker.all_finished.connect(self._on_all_finished)
        self._worker.start()

    def _on_batch_progress(self, progress: PipelineProgress):
        self.progress_bar.setValue(int(progress.progress * 100))
        self.progress_label.setText(f"总体进度: {progress.message}")

    def _on_item_finished(self, script_path: str, success: bool, message: str):
        for i in range(self.script_list.count()):
            item = self.script_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == script_path:
                if success:
                    item.setData(Qt.ItemDataRole.UserRole + 1, self.STATUS_DONE)
                    display = f"✓ {os.path.basename(script_path)}"
                    item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    item.setData(Qt.ItemDataRole.UserRole + 1, self.STATUS_ERROR)
                    display = f"✗ {os.path.basename(script_path)} ({message[:30]})"
                    item.setForeground(Qt.GlobalColor.red)
                item.setText(display)
                break

    def _on_all_finished(self, results: list):
        self.btn_start.setText("▶ 开始批量处理")
        self.btn_start.setObjectName("primary_btn")
        self.style().unpolish(self.btn_start)
        self.style().polish(self.btn_start)
        self.progress_label.setText("批量处理完成")
        self._worker = None

        success_count = sum(1 for _, s, _ in results if s)
        QMessageBox.information(
            self, "批量处理完成",
            f"处理完成: {success_count}/{len(results)} 成功"
        )

    def _open_output(self):
        output_dir_text = self.output_dir_label.text().replace("输出: ", "")
        if os.path.exists(output_dir_text):
            os.startfile(output_dir_text)

    def _update_start_button(self):
        has_items = self.script_list.count() > 0
        self.btn_start.setEnabled(has_items)
