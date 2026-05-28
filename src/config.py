from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import os

class Settings(BaseSettings):
    # uato read settings
    model_config = SettingsConfigDict(toml_file="settings.toml")

    # po umolchanio
    watch_dirs: list[Path] = Field(default=[Path("./media")])
    output_dir: Path = Field(default=Path("./output"))

    # setting for img
    image_quality: int = Field(default=85, ge=1, le=100)
    image_formats: list[str] = Field(default=["webp", "avif"])

    # settings for video
    video_codec: str = Field(default="libx264")
    video_crf: int = Field(default=23, ge=0, le=51)

    # work potok
    max_workers: int = Field(default=4, ge=1)

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
