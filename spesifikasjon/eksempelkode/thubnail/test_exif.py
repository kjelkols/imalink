import sqlite3
from pathlib import Path
from PIL import Image, ExifTags
import hashlib
from io import BytesIO
import json

# --- Config ---
DB_FILE = "photos.db"
SRC_DIR = Path(r"C:\temp\PHOTOS_SRC_TEST_MICRO")
THUMB_SIZE = (80, 80)

# --- Database ---
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    hash TEXT UNIQUE,
    path TEXT,
    thumb BLOB,
    exif TEXT
)
""")
conn.commit()

# --- Functions ---
def make_thumbnail(image_path, size=THUMB_SIZE):
    """Create RGB thumbnail"""
    with Image.open(image_path) as img:
        img = img.convert('RGB')
        img.thumbnail(size)
        return img

def image_to_pixel_bytes(img):
    return img.tobytes()

def hash_thumbnail(img):
    pixel_bytes = image_to_pixel_bytes(img)
    return hashlib.sha256(pixel_bytes).hexdigest()

def save_thumbnail(img):
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def extract_exif(image_path):
    """Extract EXIF metadata as dict"""
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if not exif:
                return {}
            exif_data = {}
            for tag, value in exif.items():
                value = str(value)
                
                tag_name = ExifTags.TAGS.get(tag, str(tag))
                if isinstance(value, bytes):
                    value = "????bytes????"  # Avoid storing raw bytes
                else:
                    value = str(value)
                exif_data[tag_name] = value
            return exif_data
    except Exception:
        return {"Error": "Could not extract EXIF"}

def process_image_file(image_path: Path):
    try:
        thumb = make_thumbnail(image_path)
        h = hash_thumbnail(thumb)
        thumb_bytes = save_thumbnail(thumb)
        serializable_exif = extract_exif(image_path)
        # Remove non-serializable values from exif_dict and convert bytes to base64 string
#        serializable_exif = exif_dict #{k: make_serializable(v) for k, v in exif_dict.items()}
        for key in serializable_exif:
            print("    ", key, type(serializable_exif[key]), serializable_exif[key])
        print ("-----")
        
        print(type(serializable_exif), f"EXIF for {image_path}: {serializable_exif}")
        exif_json = json.dumps(serializable_exif)

        cur.execute("INSERT INTO photos (hash, path, thumb, exif) VALUES (?, ?, ?, ?)",
                    (h, str(image_path), thumb_bytes, exif_json))
        conn.commit()
        print(f"Added: {image_path} (hash={h[:8]}...)")
    except sqlite3.IntegrityError:
        print(f"Already in DB: {image_path}")

# --- Indexing phase ---
print("Indexing images...")
for file_path in SRC_DIR.rglob("*.*"):
    if file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
        process_image_file(file_path)

print("\nIndexing done.")
print("You can now query EXIF fields, e.g.:")
print("  Model = Canon EOS 80D")
print("  DateTimeOriginal LIKE 2023%")
print("Type 'exit' to quit.\n")

# --- Interactive query loop ---
while True:
    user_input = input("EXIF query (e.g. Model=Canon): ").strip()
    if user_input.lower() in ("exit", "quit"):
        break

    # Split into key/value
    if "=" in user_input:
        key, value = user_input.split("=", 1)
        key, value = key.strip(), value.strip()

        sql = "SELECT path FROM photos WHERE json_extract(exif, ?) = ?"
        param = f"$.{key}"
        rows = cur.execute(sql, (param, value)).fetchall()

    elif "LIKE" in user_input.upper():
        # Example: DateTimeOriginal LIKE 2023%
        try:
            key, value = user_input.split("LIKE", 1)
            key, value = key.strip(), value.strip()
            sql = "SELECT path FROM photos WHERE json_extract(exif, ?) LIKE ?"
            param = f"$.{key}"
            rows = cur.execute(sql, (param, value)).fetchall()
        except ValueError:
            print("Invalid LIKE query. Example: DateTimeOriginal LIKE 2023%")
            continue
    else:
        print("Invalid input. Use 'Field=Value' or 'Field LIKE pattern'")
        continue

    if rows:
        print("Matches:")
        for (path,) in rows:
            print("  ", path)
    else:
        print("No matches found.")

conn.close()
