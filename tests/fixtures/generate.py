from PIL import Image
from pathlib import Path

base = Path(__file__).parent
(base / "expected").mkdir(exist_ok=True)

img = Image.new("RGB", (100, 100), color=(255, 0, 0))
img.save(base / "sample.jpg", "JPEG", quality=85)
img.save(base / "sample.png", "PNG")
print("fixtures created")