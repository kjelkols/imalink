import sqlite3
from pathlib import Path
from PIL import Image
import hashlib
from io import BytesIO

# --- Konfig ---
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
    thumb BLOB
)
""")
conn.commit()

# --- Funksjoner ---
def make_thumbnail(image_path, size=THUMB_SIZE):
    """Lag thumbnail i RGB-format"""
    with Image.open(image_path) as img:
        img = img.convert('RGB')
        img.thumbnail(size)
        return img

def image_to_pixel_bytes(img):
    """Konverter pixel-data til bytes"""
    return img.tobytes()

def hash_thumbnail(img):
    """Lag SHA256-hash fra pixel-data"""
    pixel_bytes = image_to_pixel_bytes(img)
    return hashlib.sha256(pixel_bytes).hexdigest()

def save_thumbnail(img):
    """Lagre thumbnail som JPEG-bytes"""
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def process_image_file(image_path: Path):
    """Generer hash + thumbnail og lagre i DB"""
    try:
        thumb = make_thumbnail(image_path)
        h = hash_thumbnail(thumb)
        thumb_bytes = save_thumbnail(thumb)

        cur.execute("INSERT INTO photos (hash, path, thumb) VALUES (?, ?, ?)",
                    (h, str(image_path), thumb_bytes))
        conn.commit()
        print(f"Lagt til: {image_path} (hash={h[:8]}...)")
    except sqlite3.IntegrityError:
        print(f"Allerede i DB: {image_path}")

# --- Behandle alle bilder ---
for file_path in SRC_DIR.rglob("*.*"):
    if file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
        process_image_file(file_path)

conn.close()
