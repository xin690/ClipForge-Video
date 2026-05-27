from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QFont

from core.models import Timeline, TimelineItem


class TimelineView(QWidget):
    COLOR_MAP = {
        "normal": QColor("#89b4fa"),
        "big_yellow": QColor("#f9e2af"),
        "soft_white": QColor("#bac2de"),
        "bold": QColor("#f38ba8"),
    }

    def __init__(self):
        super().__init__()
        self._timeline: Timeline | None = None
        self._item_widths: list[float] = []
        self._pixels_per_second = 60.0
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)

    def set_timeline(self, timeline: Timeline | None):
        self._timeline = timeline
        self._item_widths = []
        if timeline and timeline.timeline:
            total_duration = timeline.timeline[-1].end
            available_width = max(self.width() - 40, 200)
            self._pixels_per_second = available_width / max(total_duration, 1)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor("#1e1e2e")
        painter.fillRect(self.rect(), bg)

        if not self._timeline or not self._timeline.timeline:
            painter.setPen(QColor("#6c7086"))
            painter.setFont(QFont("Microsoft YaHei", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无 Timeline 数据")
            return

        margin = 10
        y = 20
        height = 80
        x = margin

        for i, item in enumerate(self._timeline.timeline):
            duration = item.end - item.start
            w = max(duration * self._pixels_per_second, 20)

            color = self.COLOR_MAP.get(item.subtitle_style, QColor("#89b4fa"))
            rect = QRectF(int(x), y, int(w), height)

            painter.setBrush(QBrush(color))
            if i == self._selected_index:
                painter.setPen(QPen(QColor("#f5c2e7"), 2))
            else:
                painter.setPen(QPen(color.darker(120), 1))
            painter.drawRoundedRect(rect, 4, 4)

            painter.setPen(QColor("#1e1e2e"))
            painter.setFont(QFont("Microsoft YaHei", 9))
            text = f"{item.subtitle[:12]}..." if len(item.subtitle) > 12 else item.subtitle
            painter.drawText(rect.adjusted(4, 2, -4, -2), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

            painter.setPen(QColor("#6c7086"))
            painter.setFont(QFont("Consolas", 8))
            time_text = f"{item.start:.1f}s-{item.end:.1f}s"
            painter.drawText(rect.adjusted(4, height - 14, -4, -2), Qt.AlignmentFlag.AlignLeft, time_text)

            x += w
            self._item_widths.append(w)

        total_duration = self._timeline.timeline[-1].end

        painter.setPen(QPen(QColor("#313244"), 1))
        painter.drawLine(margin, y + height + 8, int(x), y + height + 8)

        for i, item in enumerate(self._timeline.timeline):
            px = margin + sum(self._item_widths[:i])
            painter.setPen(QColor("#6c7086"))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(px) - 10, y + height + 22, f"{item.start:.0f}s")

        painter.drawText(int(x) - 20, y + height + 22, f"{total_duration:.0f}s")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._timeline and self._timeline.timeline:
            total_duration = self._timeline.timeline[-1].end
            available_width = max(self.width() - 40, 200)
            self._pixels_per_second = available_width / max(total_duration, 1)


class TimelinePreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = QLabel("时间轴预览")
        title.setObjectName("heading")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("subheading")
        header.addWidget(self.status_label)

        layout.addLayout(header)

        self.timeline_view = TimelineView()
        layout.addWidget(self.timeline_view)

    def set_timeline(self, timeline: Timeline | None):
        self.timeline_view.set_timeline(timeline)
        if timeline and timeline.timeline:
            total = timeline.timeline[-1].end
            count = len(timeline.timeline)
            self.status_label.setText(f"{count} 个镜头 · 总时长 {total:.1f}s")
        else:
            self.status_label.setText("")
