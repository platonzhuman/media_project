from dataclasses import dataclass


@dataclass
class ConversionResult:
    output_bytes: bytes
    original_size: int
    output_size: int
    format: str
    saved_bytes: int
    ratio: float


@dataclass
class MediaFile:
    data: bytes
    filename: str
    format: str
    size: int