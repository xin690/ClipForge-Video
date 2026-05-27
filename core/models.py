from pydantic import BaseModel, Field
from typing import Optional, Literal


class Segment(BaseModel):
    id: int
    text: str
    keywords: list[str] = []
    emotion: str = "normal"
    duration: int = Field(gt=0, le=60, default=5)


class Script(BaseModel):
    title: str
    duration: int = Field(gt=0, le=3600)
    style: str = "knowledge"
    voice: str = "zh-CN-XiaoxiaoNeural"
    bgm: str = ""
    segments: list[Segment] = Field(min_length=1)


class Asset(BaseModel):
    id: int = 0
    file: str
    type: Literal["video", "image", "bgm", "voice"]
    duration: Optional[float] = None
    width: int = 0
    height: int = 0
    tags: list[str] = []
    file_size: int = 0
    created_at: str = ""


class TimelineItem(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    asset: str
    asset_type: str = "video"
    transition: str = "cut"
    subtitle: str = ""
    subtitle_style: str = "normal"
    subtitle_animation: str = "none"
    camera: str = "static"
    voice_file: Optional[str] = None
    bgm_file: Optional[str] = None


class Timeline(BaseModel):
    timeline: list[TimelineItem] = Field(min_length=1)
    output_path: str = ""
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 30


class Project(BaseModel):
    name: str = "未命名项目"
    script_path: str = ""
    output_path: str = ""
    created_at: str = ""
    updated_at: str = ""
