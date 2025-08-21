import sqlite3
from config import DB_PATH
from typing import Optional, List
from models import SourceFile

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sourcefiles (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            thumbnail BLOB,
            exif_data BLOB
        )
    ''')
    conn.commit()
    conn.close()

def add_sourcefile(filename, thumbnail, exif_data):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO sourcefiles (filename, thumbnail, exif_data)
        VALUES (?, ?, ?)
    ''', (filename, thumbnail, exif_data))
    conn.commit()
    conn.close()

def get_sourcefile_by_id(sourcefile_id: int) -> Optional[SourceFile]:
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, filename, thumbnail, exif_data FROM sourcefiles WHERE id = ?', (sourcefile_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return SourceFile(id=row[0], filename=row[1], thumbnail=row[2], exif_data=row[3])
    return None

def get_all_sourcefiles() -> List[SourceFile]:
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, filename, thumbnail, exif_data FROM sourcefiles')
    rows = c.fetchall()
    conn.close()
    return [SourceFile(id=row[0], filename=row[1], thumbnail=row[2], exif_data=row[3]) for row in rows]

def update_sourcefile(sourcefile_id: int, filename: str, thumbnail: bytes, exif_data: bytes) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE sourcefiles
        SET filename = ?, thumbnail = ?, exif_data = ?
        WHERE id = ?
    ''', (filename, thumbnail, exif_data, sourcefile_id))
    conn.commit()
    updated = c.rowcount > 0
    conn.close()
    return updated

def delete_sourcefile(sourcefile_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM sourcefiles WHERE id = ?', (sourcefile_id,))
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return deleted

if __name__ == "__main__":
    init_db()
    print("Database initialized.")