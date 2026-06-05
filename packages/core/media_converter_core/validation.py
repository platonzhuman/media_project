def validate_quality(quality: int) -> int:
    if not 1 <= quality <= 100:
        raise ValueError(f"quality должен быть 1–100, получен {quality}")
    return quality


def validate_crf(crf: int) -> int:
    if not 0 <= crf <= 51:
        raise ValueError(f"crf должен быть 0–51, получен {crf}")
    return crf


def validate_paths(watch_dirs, output_dir) -> None:
    for d in watch_dirs:
        if str(output_dir) == str(d):
            raise ValueError("output_dir не может совпадать с watch_dir")