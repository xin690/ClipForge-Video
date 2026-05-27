MAIN_STYLE = """
QMainWindow {
    background-color: #1e1e2e;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
}
QMenuBar::item:selected {
    background-color: #313244;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
}
QMenu::item:selected {
    background-color: #313244;
}
QTabWidget::pane {
    background-color: #1e1e2e;
    border: none;
}
QTabBar::tab {
    background-color: #181825;
    color: #6c7086;
    padding: 8px 24px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover {
    color: #cdd6f4;
}
QStatusBar {
    background-color: #181825;
    color: #6c7086;
    border-top: 1px solid #313244;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: none;
    padding: 6px 16px;
    border-radius: 4px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
}
QPushButton#primary_btn {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
}
QPushButton#primary_btn:hover {
    background-color: #74c7ec;
}
QPushButton#danger_btn {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#danger_btn:hover {
    background-color: #eba0ac;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #89b4fa;
}
QTableView, QTableWidget, QTreeView, QListView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    gridline-color: #313244;
    selection-background-color: #313244;
}
QTableView::item:hover, QTableWidget::item:hover {
    background-color: #313244;
}
QHeaderView::section {
    background-color: #181825;
    color: #6c7086;
    border: none;
    border-bottom: 1px solid #313244;
    padding: 4px 8px;
}
QLabel {
    color: #cdd6f4;
}
QLabel#heading {
    font-size: 16px;
    font-weight: bold;
    color: #cdd6f4;
    padding: 8px 0;
}
QLabel#subheading {
    font-size: 12px;
    color: #6c7086;
}
QCheckBox {
    color: #cdd6f4;
}
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}
QComboBox:hover {
    border: 1px solid #89b4fa;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}
QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QSplitter::handle {
    background-color: #313244;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}
QDialog {
    background-color: #1e1e2e;
}
QGroupBox {
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
}
QGroupBox::title {
    color: #cdd6f4;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QSpinBox, QDoubleSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
    min-height: 24px;
}
QSlider::groove:horizontal {
    background-color: #313244;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #89b4fa;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background-color: #89b4fa;
    border-radius: 2px;
}
"""


def get_style() -> str:
    return MAIN_STYLE
