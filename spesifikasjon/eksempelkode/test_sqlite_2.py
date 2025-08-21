from pathlib import Path
from collections import defaultdict

source_path = Path(r"C:\temp\PHOTOS_SRC_TEST_MICRO")

# Alle relevante filer
extensions = [".jpg", ".jpeg", ".raw", ".nef", ".cr2", ".fake_raw"]  # legg til flere raw-formater om ønskelig
files = list(source_path.rglob("*.*"))

# Grupper filer etter "base name" (uten filtype)
images = defaultdict(dict)

for f in files:
    if f.suffix.lower() in extensions:
        base_name = f.stem  # filnavn uten filtype
        if f.suffix.lower() in [".jpg", ".jpeg"]:
            images[base_name]["jpeg"] = f
        else:
            images[base_name]["raw"] = f

# Test: print ut alle grupper
for name, group in images.items():
    print(f"Image: {name}")
    if "jpeg" in group:
        print(f"  JPEG: {group['jpeg']}")
    if "raw" in group:
        print(f"  RAW: {group['raw']}")
