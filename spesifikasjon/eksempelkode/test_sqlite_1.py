import os
import sqlite3
from pathlib import Path

from pathlib import Path

# Databasefil
db_path = "photos.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Opprett tabeller (hvis ikke allerede opprettet)
cursor.execute("""
CREATE TABLE IF NOT EXISTS Photo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS PhotoFile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id INTEGER,
    file_path TEXT,
    file_type TEXT,
    FOREIGN KEY(photo_id) REFERENCES Photo(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT
)
""")

conn.commit()

# Testkilde
source_path = Path(r"C:\temp\PHOTOS_SRC_TEST_MICRO")
source_name = source_path.name

# Legg til kilde i Source-tabellen
cursor.execute("INSERT INTO Source (name) VALUES (?)", (source_name,))
source_id = cursor.lastrowid
conn.commit()


# Finn alle jpg/jpeg/raw-filer rekursivt
files = list(source_path.rglob("*.*"))  # rglob går gjennom alle underkataloger

for f in files:
    if f.suffix.lower() in [".jpg", ".jpeg", ".raw", ".nef", ".cr2"]:
        print(f)


# Legg til filer
for file in source_path.iterdir():
    if file.suffix.lower() in [".jpg", ".jpeg", ".raw", ".nef", ".cr2"]:  # legg til RAW-typer du ønsker
        # Opprett Photo
        cursor.execute("INSERT INTO Photo (name) VALUES (?)", (file.stem,))
        photo_id = cursor.lastrowid
        
        # Legg til filen
        cursor.execute(
            "INSERT INTO PhotoFile (photo_id, file_path, file_type) VALUES (?, ?, ?)",
            (photo_id, str(file), file.suffix.lower())
        )


conn.commit()
conn.close()

print("Import ferdig!")
