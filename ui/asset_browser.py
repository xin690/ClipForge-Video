import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableView, QHeaderView, QLineEdit, QComboBox, QMessageBox,
    QFileDialog, QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor

from core.database import Database
from core.models import Asset
from core.config import get


class AssetTableModel(QAbstractTableModel):
    HEADERS = ["文件名", "类型", "时长(s)", "标签", "尺寸", "大小(B)"]
    FIELD_MAP = ["file", "type", "duration", "tags", "resolution", "file_size"]

    def __init__(self):
        super().__init__()
        self._assets: list[Asset] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._assets)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._assets):
            return None

        asset = self._assets[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return asset.file
            elif col == 1:
                return asset.type
            elif col == 2:
                return f"{asset.duration:.1f}" if asset.duration else "-"
            elif col == 3:
                return ", ".join(asset.tags) if asset.tags else "-"
            elif col == 4:
                return f"{asset.width}x{asset.height}" if asset.width > 0 else "-"
            elif col == 5:
                return str(asset.file_size)

        if role == Qt.ItemDataRole.ForegroundRole:
            type_colors = {
                "video": QColor("#89b4fa"),
                "image": QColor("#a6e3a1"),
                "bgm": QColor("#fab387"),
                "voice": QColor("#cba6f7"),
            }
            if col == 1:
                return type_colors.get(asset.type, QColor("#cdd6f4"))

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def load(self, assets: list[Asset]):
        self.beginResetModel()
        self._assets = assets
        self.endResetModel()

    def get_asset(self, row: int) -> Asset | None:
        if 0 <= row < len(self._assets):
            return self._assets[row]
        return None


class AssetBrowserTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = main_window.db
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        header = QHBoxLayout()
        title = QLabel("素材管理")
        title.setObjectName("heading")
        header.addWidget(title)
        header.addStretch()

        self.btn_scan = QPushButton("扫描素材库")
        self.btn_scan.clicked.connect(self._scan)
        header.addWidget(self.btn_scan)

        self.btn_import = QPushButton("导入素材")
        self.btn_import.clicked.connect(self._import)
        header.addWidget(self.btn_import)

        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.setObjectName("danger_btn")
        self.btn_delete.clicked.connect(self._delete_selected)
        header.addWidget(self.btn_delete)

        self.count_label = QLabel("")
        self.count_label.setObjectName("subheading")
        header.addWidget(self.count_label)

        layout.addLayout(header)

        filter_bar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索素材（关键词）...")
        self.search_input.textChanged.connect(self._filter)
        filter_bar.addWidget(self.search_input, 1)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部", "video", "image", "bgm", "voice"])
        self.type_filter.currentTextChanged.connect(self._filter)
        filter_bar.addWidget(self.type_filter)

        layout.addLayout(filter_bar)

        self.model = AssetTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #181825;")
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

    def refresh(self):
        assets = self.db.get_all_assets()
        self.model.load(assets)
        self.count_label.setText(f"共 {len(assets)} 个素材")

    def _scan(self):
        self.main_window._scan_assets()

    def _import(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择素材文件",
            "",
            "视频 (*.mp4 *.mov *.avi *.mkv);;图片 (*.jpg *.png);;音频 (*.mp3 *.wav);;所有文件 (*)"
        )
        if not files:
            return

        assets_dir = get("paths.assets", "./assets")
        count = 0

        for file_path in files:
            ext = Path(file_path).suffix.lower()
            ext_map = {
                ".mp4": "videos", ".mov": "videos", ".avi": "videos", ".mkv": "videos",
                ".jpg": "images", ".jpeg": "images", ".png": "images", ".gif": "images",
                ".mp3": "bgm", ".wav": "bgm", ".ogg": "bgm", ".flac": "bgm",
            }
            subdir = ext_map.get(ext, "videos")
            dest_dir = Path(assets_dir) / subdir
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / Path(file_path).name

            import shutil
            try:
                shutil.copy2(file_path, str(dest_path))
                count += 1
            except Exception as e:
                QMessageBox.warning(self, "导入失败", str(e))

        if count > 0:
            self.main_window._run_scan(assets_dir)

    def _delete_selected(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(indexes)} 个素材记录?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for index in indexes:
            source_index = self.proxy.mapToSource(index)
            asset = self.model.get_asset(source_index.row())
            if asset:
                self.db.delete_asset(asset.id)

        self.refresh()
        self.main_window.update_asset_count()

    def _filter(self):
        keyword = self.search_input.text().strip()
        type_filter = self.type_filter.currentText()

        if type_filter == "全部":
            type_filter = ""

        if keyword:
            assets = self.db.search_assets(keyword=keyword, type_filter=type_filter, limit=500)
        elif type_filter:
            assets = self.db.search_assets(type_filter=type_filter, limit=500)
        else:
            assets = self.db.get_all_assets()

        self.model.load(assets)
        self.count_label.setText(f"共 {len(assets)} 个素材")
