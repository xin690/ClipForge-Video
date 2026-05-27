from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QFileDialog, QMessageBox, QTabWidget,
    QWidget, QSlider,
)
from PyQt6.QtCore import Qt

from core.config import get_config, save_config, get


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("偏好设置")
        self.setMinimumSize(600, 500)
        self._config = get_config()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self.input_assets_dir = QLineEdit()
        self.btn_browse_assets = QPushButton("浏览...")
        self.btn_browse_assets.clicked.connect(lambda: self._browse_dir(self.input_assets_dir))
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.input_assets_dir, 1)
        dir_layout.addWidget(self.btn_browse_assets)
        general_layout.addRow("素材目录:", dir_layout)

        self.input_output_dir = QLineEdit()
        self.btn_browse_output = QPushButton("浏览...")
        self.btn_browse_output.clicked.connect(lambda: self._browse_dir(self.input_output_dir))
        dir_layout2 = QHBoxLayout()
        dir_layout2.addWidget(self.input_output_dir, 1)
        dir_layout2.addWidget(self.btn_browse_output)
        general_layout.addRow("输出目录:", dir_layout2)

        self.combo_resolution = QComboBox()
        self.combo_resolution.addItems(["1920x1080", "1280x720", "1080x1920", "3840x2160"])
        general_layout.addRow("默认分辨率:", self.combo_resolution)

        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(24, 60)
        general_layout.addRow("FPS:", self.spin_fps)

        tabs.addTab(general_tab, "通用")

        tts_tab = QWidget()
        tts_layout = QFormLayout(tts_tab)

        self.combo_tts_engine = QComboBox()
        self.combo_tts_engine.addItems(["edge-tts", "piper"])
        tts_layout.addRow("TTS 引擎:", self.combo_tts_engine)

        self.combo_voice = QComboBox()
        self.combo_voice.addItems([
            "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural",
            "zh-CN-YunxiNeural", "zh-CN-YunyangNeural",
        ])
        tts_layout.addRow("语音:", self.combo_voice)

        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.5, 2.0)
        self.spin_speed.setSingleStep(0.1)
        tts_layout.addRow("语速:", self.spin_speed)

        tabs.addTab(tts_tab, "配音")

        subtitle_tab = QWidget()
        subtitle_layout = QFormLayout(subtitle_tab)

        self.combo_sub_mode = QComboBox()
        self.combo_sub_mode.addItems(["text", "whisper"])
        subtitle_layout.addRow("字幕模式:", self.combo_sub_mode)

        self.combo_whisper = QComboBox()
        self.combo_whisper.addItems(["tiny", "base", "small"])
        subtitle_layout.addRow("Whisper 模型:", self.combo_whisper)

        tabs.addTab(subtitle_tab, "字幕")

        render_tab = QWidget()
        render_layout = QFormLayout(render_tab)

        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"])
        render_layout.addRow("编码预设:", self.combo_preset)

        self.spin_crf = QSpinBox()
        self.spin_crf.setRange(0, 51)
        render_layout.addRow("CRF 质量 (0~51):", self.spin_crf)

        self.spin_bgm_volume = QDoubleSpinBox()
        self.spin_bgm_volume.setRange(0.0, 1.0)
        self.spin_bgm_volume.setSingleStep(0.05)
        render_layout.addRow("BGM 音量:", self.spin_bgm_volume)

        tabs.addTab(render_tab, "渲染")

        ai_tab = QWidget()
        ai_layout = QFormLayout(ai_tab)

        self.check_ai = QCheckBox("启用 AI 规划")
        ai_layout.addRow("", self.check_ai)

        self.combo_ai_provider = QComboBox()
        self.combo_ai_provider.addItems(["openai", "qwen", "deepseek"])
        ai_layout.addRow("API 提供商:", self.combo_ai_provider)

        self.input_api_key = QLineEdit()
        self.input_api_key.setPlaceholderText("输入你的 API Key")
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_layout.addRow("API Key:", self.input_api_key)

        self.combo_ai_model = QComboBox()
        self.combo_ai_model.addItems(["gpt-4o-mini", "gpt-4o", "qwen-plus", "qwen-turbo", "deepseek-chat"])
        ai_layout.addRow("模型:", self.combo_ai_model)

        tabs.addTab(ai_tab, "AI")

        layout.addWidget(tabs, 1)

        btn_layout = QHBoxLayout()
        self.btn_reset = QPushButton("恢复默认")
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("保存")
        self.btn_save.setObjectName("primary_btn")
        self.btn_save.clicked.connect(self._save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        self.input_assets_dir.setText(get("paths.assets", "./assets"))
        self.input_output_dir.setText(get("paths.output", "./output"))

        res = f"{get('video.width', 1920)}x{get('video.height', 1080)}"
        idx = self.combo_resolution.findText(res)
        if idx >= 0:
            self.combo_resolution.setCurrentIndex(idx)

        self.spin_fps.setValue(get("video.fps", 30))
        self.combo_tts_engine.setCurrentText(get("tts.engine", "edge-tts"))
        self.combo_voice.setCurrentText(get("tts.voice", "zh-CN-XiaoxiaoNeural"))
        self.spin_speed.setValue(get("tts.speed", 1.0))
        self.combo_sub_mode.setCurrentText(get("subtitle.engine", "text"))
        self.combo_whisper.setCurrentText(get("subtitle.whisper_model", "tiny"))
        self.combo_preset.setCurrentText(get("video.preset", "veryfast"))
        self.spin_crf.setValue(get("video.crf", 23))
        self.spin_bgm_volume.setValue(get("bgm.volume", 0.3))
        self.check_ai.setChecked(get("ai.enabled", False))
        self.combo_ai_provider.setCurrentText(get("ai.provider", "openai"))
        self.input_api_key.setText(get("ai.api_key", ""))
        self.combo_ai_model.setCurrentText(get("ai.model", "gpt-4o-mini"))

    def _save(self):
        res_text = self.combo_resolution.currentText()
        w, h = res_text.split("x")

        self._config["paths"]["assets"] = self.input_assets_dir.text()
        self._config["paths"]["output"] = self.input_output_dir.text()
        self._config["video"]["width"] = int(w)
        self._config["video"]["height"] = int(h)
        self._config["video"]["fps"] = self.spin_fps.value()
        self._config["tts"]["engine"] = self.combo_tts_engine.currentText()
        self._config["tts"]["voice"] = self.combo_voice.currentText()
        self._config["tts"]["speed"] = self.spin_speed.value()
        self._config["subtitle"]["engine"] = self.combo_sub_mode.currentText()
        self._config["subtitle"]["whisper_model"] = self.combo_whisper.currentText()
        self._config["video"]["preset"] = self.combo_preset.currentText()
        self._config["video"]["crf"] = self.spin_crf.value()
        self._config["bgm"]["volume"] = self.spin_bgm_volume.value()
        self._config["ai"]["enabled"] = self.check_ai.isChecked()
        self._config["ai"]["provider"] = self.combo_ai_provider.currentText()
        self._config["ai"]["api_key"] = self.input_api_key.text()
        self._config["ai"]["model"] = self.combo_ai_model.currentText()

        save_config(self._config)
        QMessageBox.information(self, "提示", "设置已保存")
        self.accept()

    def _reset_defaults(self):
        from core.config import _default_config
        self._config = _default_config()
        self._load_settings()

    def _browse_dir(self, line_edit: QLineEdit):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录", line_edit.text())
        if dir_path:
            line_edit.setText(dir_path)
