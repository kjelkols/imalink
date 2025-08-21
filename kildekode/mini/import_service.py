import os
from PIL import Image
import io
import json
from ..database import get_connection, init_db
from ..config import THUMBNAIL_SIZE
from .exif_service import extract_exif

def import_photos(source_dir):
    init_db()
    conn = get_connection()
    c = conn.cursor()

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg")):
                full_path = os.path.join(root, file)
                print(f"Importerer: {full_path}")

                # Lag thumbnail
                thumbnail = create_thumbnail(full_path)

                # Hent EXIF-data
                exif_data = extract_exif(full_path)
                exif_json = json.dumps(exif_data, ensure_ascii=False)

                # Lagre i database
                c.execute(
                    "INSERT INTO photos (filename, thumbnail, exif_data) VALUES (?, ?, ?)",
                    (full_path, thumbnail, exif_json)
                )

    conn.commit()
    conn.close()

def create_thumbnail(image_path):
    with Image.open(image_path) as img:
        img.thumbnail(THUMBNAIL_SIZE)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
