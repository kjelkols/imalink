from pathlib import Path
from collections import defaultdict
import sqlite3
from datetime import datetime

# ====== Konfig ======
source_path = Path(r"C:\temp\PHOTOS_SRC_TEST_MICRO")
db_path = Path("images.db")
extensions = [".jpg", ".jpeg", ".raw", ".nef", ".cr2", ".fake_raw"]  # legg til raw-formater du bruker

# ====== Funksjon: opprett database ======
def create_database(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    
    # Tabell for bilder
    c.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        jpeg_path TEXT,
        raw_path TEXT,
        import_date TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database opprettet: {db_file}")

# ====== Funksjon: importer bilder ======
def import_images(db_file, source_folder):
    files = list(source_folder.rglob("*.*"))
    images_dict = defaultdict(dict)

    for f in files:
        if f.suffix.lower() in extensions:
            base_name = f.stem
            if f.suffix.lower() in [".jpg", ".jpeg"]:
                images_dict[base_name]["jpeg"] = str(f)
            else:
                images_dict[base_name]["raw"] = str(f)

    image_objects = []
    for name, group in images_dict.items():
        image_objects.append({
            "name": name,
            "jpeg_path": group.get("jpeg"),
            "raw_path": group.get("raw"),
            "import_date": datetime.now().isoformat()
        })

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    for img in image_objects:
        # Sett inn eller oppdater hvis filtype mangler
        c.execute("""
        INSERT INTO images (name, jpeg_path, raw_path, import_date)
        VALUES (:name, :jpeg_path, :raw_path, :import_date)
        ON CONFLICT(name) DO UPDATE SET
            jpeg_path=COALESCE(excluded.jpeg_path, images.jpeg_path),
            raw_path=COALESCE(excluded.raw_path, images.raw_path),
            import_date=excluded.import_date
        """, img)

    conn.commit()
    conn.close()
    print(f"{len(image_objects)} bilder importert/oppdatert i databasen.")

# ====== Hovedprogram ======
if __name__ == "__main__":
    create_database(db_path)
    import_images(db_path, source_path)
