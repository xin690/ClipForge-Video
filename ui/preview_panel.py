from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QFrame,
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class PreviewPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(320, 240)
        self.video_widget.setStyleSheet("background-color: #181825;")
        layout.addWidget(self.video_widget, 1)

        controls = QHBoxLayout()

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_play.clicked.connect(self._toggle_play)
        controls.addWidget(self.btn_play)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self._seek)
        controls.addWidget(self.progress_slider, 1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("subheading")
        controls.addWidget(self.time_label)

        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setFixedWidth(40)
        self.volume_btn.setCheckable(True)
        self.volume_btn.clicked.connect(self._toggle_mute)
        controls.addWidget(self.volume_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        controls.addWidget(self.volume_slider)

        layout.addLayout(controls)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.volume_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v / 100.0))

    def play(self, file_path: str):
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

    def stop(self):
        self.player.stop()

    def _toggle_mute(self, checked: bool):
        self.audio_output.setMuted(checked)
        self.volume_btn.setText("🔇" if checked else "🔊")

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _seek(self, position: int):
        duration = self.player.duration()
        if duration > 0:
            self.player.setPosition(int(position * duration / 100))

    def _on_position_changed(self, position: int):
        duration = self.player.duration()
        if duration > 0:
            self.progress_slider.setValue(int(position * 100 / duration))
            self.time_label.setText(
                f"{self._fmt_time(position)} / {self._fmt_time(duration)}"
            )

    def _on_duration_changed(self, duration: int):
        self.time_label.setText(f"00:00 / {self._fmt_time(duration)}")

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def _fmt_time(self, ms: int) -> str:
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
