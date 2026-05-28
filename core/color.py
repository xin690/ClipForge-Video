import os
from core.config import get as _config_get


EMOTION_GRADING: dict[str, str] = {
    "normal": "eq=brightness=0.02:contrast=1.05:saturation=1.00",
    "strong": "eq=brightness=-0.02:contrast=1.20:saturation=1.15,vignette=PI/5",
    "calm":   "eq=brightness=0.03:contrast=0.95:saturation=0.85:gamma=1.05",
    "happy":  "eq=brightness=0.05:contrast=1.05:saturation=1.25:gamma=1.02",
    "sad":    "eq=brightness=-0.03:contrast=0.90:saturation=0.70",
}


def get_emotion_grade(emotion: str) -> str:
    if not _config_get("visual.color.enable_emotion_grading", True):
        return ""
    return EMOTION_GRADING.get(emotion, "")


def get_lut_filter() -> str:
    lut_path = _config_get("visual.color.lut_path", "")
    if not lut_path or not os.path.isdir(lut_path):
        return ""
    import glob as _glob
    cube_files = _glob.glob(os.path.join(lut_path, "*.cube"))
    if not cube_files:
        return ""
    first = cube_files[0].replace("\\", "/").replace(":", "\\:")
    return f"lut3d='{first}':interp=trilinear"


def get_zoom_speed() -> float:
    return float(_config_get("visual.camera.zoom_speed", 0.0015) or 0.0015)


def get_max_zoom() -> float:
    return float(_config_get("visual.camera.max_zoom", 1.5) or 1.5)
