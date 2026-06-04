from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import os

# vnutr models
class _CompressionImage(BaseSettings):
    quality: int = Field(default=85, ge=1, le=100)
    formats: list[str] = Field(default=["webp", "avif"])

class _CompressionVideo(BaseSettings):
    codec: str = Field(default="libx264")
    crf: int = Field(default=23, ge=0, le=51)

class _Workers(BaseSettings):
    max_workers: int = Field(default=4, ge=1)

class Settings(BaseSettings):
    # uato read settings
    model_config = SettingsConfigDict(
        toml_file="settings.toml",
        extra="ignore"  # ignore lishnie keys
    )

    # po umolchanio
    watch_dirs: list[Path] = Field(default=[Path("./media")])
    output_dir: Path = Field(default=Path("./output"))

    # input section
    compression_image: _CompressionImage = Field(default_factory=_CompressionImage)
    compression_video: _CompressionVideo = Field(default_factory=_CompressionVideo)
    workers_config: _Workers = Field(default_factory=_Workers)

    # setting for img 
    @property
    def image_quality(self) -> int:
        return self.compression_image.quality

    @property
    def image_formats(self) -> list[str]:
        return self.compression_image.formats

    # settings for video 
    @property
    def video_codec(self) -> str:
        return self.compression_video.codec

    @property
    def video_crf(self) -> int:
        return self.compression_video.crf

    # work potok 
    @property
    def max_workers(self) -> int:
        return self.workers_config.max_workers

    # for poisk directory and safe file
    @field_validator("watch_dirs", "output_dir", mode="before")
    @classmethod
    def _resolve_paths(cls, v):
        # if list - chacked all 1, 2, 3, 4, 5 ... papcks
        if isinstance(v, list):
            return [Path(p).expanduser().resolve() for p in v]
        # if one, checked one ^_^
        return Path(v).expanduser().resolve()
    
    # for auto check dirs
    @field_validator("watch_dirs")
    @classmethod
    def _check_access(cls, v: list[Path]):
        for p in v:
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
            if not os.access(p, os.W_OK | os.R_OK):
                raise ValueError(f"нет прав на папку {p}")
        return v

    # to avoid beskonechnogo range
    @field_validator("output_dir")
    @classmethod
    def _no_loop(cls, v: Path, info):
        for w in info.data.get("watch_dirs", []):
            if v.resolve() == w.resolve() or w.resolve() in v.resolve().parents:
                raise ValueError("output_dir не может быть внутри watch_dirs")
        return v

def load_settings() -> Settings:
    return Settings()