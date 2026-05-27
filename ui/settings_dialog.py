from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QFileDialog, QMessageBox, QTabWidget,
    QWidget, QSlider, QColorDialog,
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
            "zh-CN-XiaoxiaoNeural",  "zh-CN-XiaoyiNeural",
            "zh-CN-YunxiNeural",     "zh-CN-YunyangNeural",
            "zh-CN-XiaochenNeural",  "zh-CN-XiaohanNeural",
            "zh-CN-XiaomengNeural",  "zh-CN-XiaomoNeural",
            "zh-CN-XiaoqiuNeural",   "zh-CN-XiaoruiNeural",
            "zh-CN-XiaoshuangNeural","zh-CN-XiaoxuanNeural",
            "zh-CN-XiaoyanNeural",   "zh-CN-XiaoyouNeural",
            "zh-CN-YunzeNeural",     "zh-CN-YunhaoNeural",
            "zh-CN-YunjianNeural",   "zh-CN-YunxiaNeural",
            "zh-TW-HsiaoChenNeural", "zh-TW-HsiaoYuNeural",
            "zh-TW-YunJheNeural",
            "zh-HK-HiuGaaiNeural",   "zh-HK-HiuMaanNeural",
            "zh-HK-WanLungNeural",
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

        sep = QLabel("—— 以下为样式设置 ——")
        sep.setStyleSheet("color: #a6adc8; font-size: 11px;")
        subtitle_layout.addRow("", sep)

        self.combo_font_family = QComboBox()
        self.combo_font_family.setEditable(True)
        self.combo_font_family.addItems([
            "Microsoft YaHei", "SimHei", "SimSun", "FangSong",
            "KaiTi", "Microsoft JhengHei", "Noto Sans SC",
            "Source Han Sans SC", "Consolas", "Arial",
        ])
        subtitle_layout.addRow("字体:", self.combo_font_family)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(12, 120)
        subtitle_layout.addRow("字号:", self.spin_font_size)

        self.btn_font_color = QPushButton()
        self.btn_font_color.setFixedSize(40, 24)
        self.btn_font_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_font_color.clicked.connect(self._pick_color)
        subtitle_layout.addRow("颜色:", self.btn_font_color)

        self.check_bold = QCheckBox()
        subtitle_layout.addRow("粗体:", self.check_bold)

        self.spin_outline = QSpinBox()
        self.spin_outline.setRange(0, 10)
        subtitle_layout.addRow("边框:", self.spin_outline)

        self.spin_shadow = QSpinBox()
        self.spin_shadow.setRange(0, 10)
        subtitle_layout.addRow("阴影:", self.spin_shadow)

        self.combo_position = QComboBox()
        self.combo_position.addItems(["bottom", "top", "center"])
        subtitle_layout.addRow("位置:", self.combo_position)

        self.combo_animation = QComboBox()
        self.combo_animation.addItems(["none", "pulse", "swing", "fadein", "scale", "typing"])
        subtitle_layout.addRow("动画:", self.combo_animation)

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

        dl_tab = QWidget()
        dl_layout = QFormLayout(dl_tab)

        self.combo_dl_provider = QComboBox()
        self.combo_dl_provider.addItems(["pexels", "pixabay"])
        dl_layout.addRow("素材提供商:", self.combo_dl_provider)

        self.input_dl_api_key = QLineEdit()
        self.input_dl_api_key.setPlaceholderText("输入 Pexels/Pixabay API Key (免费注册)")
        self.input_dl_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        dl_layout.addRow("API Key:", self.input_dl_api_key)

        dl_note = QLabel(
            "注册地址: https://www.pexels.com/api/ (免费，200次/小时)\n"
            "或 https://pixabay.com/api/docs/ (免费，5000次/月)"
        )
        dl_note.setWordWrap(True)
        dl_note.setStyleSheet("color: #a6adc8; font-size: 11px;")
        dl_layout.addRow("", dl_note)

        tabs.addTab(dl_tab, "素材下载")

        layout.addWidget(tabs, 1)

        spin_style = """
            QSpinBox, QDoubleSpinBox {
                padding-right: 20px;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                width: 20px;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 20px;
            }
        """
        for spin in self.findChildren((QSpinBox, QDoubleSpinBox)):
            spin.setStyleSheet(spin_style)

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
        self.combo_font_family.setCurrentText(get("subtitle.font_family", "Microsoft YaHei"))
        self.spin_font_size.setValue(get("subtitle.font_size", 36))
        self._current_color = get("subtitle.font_color", "#FFFFFF")
        self.btn_font_color.setStyleSheet(f"background-color: {self._current_color};")
        self.check_bold.setChecked(get("subtitle.bold", False))
        self.spin_outline.setValue(get("subtitle.outline", 2))
        self.spin_shadow.setValue(get("subtitle.shadow", 1))
        self.combo_position.setCurrentText(get("subtitle.position", "bottom"))
        self.combo_animation.setCurrentText(get("subtitle.animation", "none"))
        self.combo_preset.setCurrentText(get("video.preset", "veryfast"))
        self.spin_crf.setValue(get("video.crf", 23))
        self.spin_bgm_volume.setValue(get("bgm.volume", 0.3))
        self.check_ai.setChecked(get("ai.enabled", False))
        self.combo_ai_provider.setCurrentText(get("ai.provider", "openai"))
        self.input_api_key.setText(get("ai.api_key", ""))
        self.combo_ai_model.setCurrentText(get("ai.model", "gpt-4o-mini"))
        self.combo_dl_provider.setCurrentText(get("downloader.provider", "pexels"))
        self.input_dl_api_key.setText(get("downloader.api_key", ""))

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
        self._config["subtitle"]["font_family"] = self.combo_font_family.currentText()
        self._config["subtitle"]["font_size"] = self.spin_font_size.value()
        self._config["subtitle"]["font_color"] = self._current_color
        self._config["subtitle"]["bold"] = self.check_bold.isChecked()
        self._config["subtitle"]["outline"] = self.spin_outline.value()
        self._config["subtitle"]["shadow"] = self.spin_shadow.value()
        self._config["subtitle"]["position"] = self.combo_position.currentText()
        self._config["subtitle"]["animation"] = self.combo_animation.currentText()
        self._config["video"]["preset"] = self.combo_preset.currentText()
        self._config["video"]["crf"] = self.spin_crf.value()
        self._config["bgm"]["volume"] = self.spin_bgm_volume.value()
        self._config["ai"]["enabled"] = self.check_ai.isChecked()
        self._config["ai"]["provider"] = self.combo_ai_provider.currentText()
        self._config["ai"]["api_key"] = self.input_api_key.text()
        self._config["ai"]["model"] = self.combo_ai_model.currentText()
        self._config["downloader"]["provider"] = self.combo_dl_provider.currentText()
        self._config["downloader"]["api_key"] = self.input_dl_api_key.text()

        save_config(self._config)
        QMessageBox.information(self, "提示", "设置已保存")
        self.accept()

    def _reset_defaults(self):
        from core.config import _default_config, save_config
        self._config = _default_config()
        save_config(self._config)
        self._load_settings()

    def _pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.btn_font_color.setStyleSheet(f"background-color: {color.name()};")
            self._current_color = color.name()

    def _browse_dir(self, line_edit: QLineEdit):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录", line_edit.text())
        if dir_path:
            line_edit.setText(dir_path)
