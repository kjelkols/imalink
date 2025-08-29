import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Iterator

from config import DB_PATH
from models import SourceFile


@contextmanager
def _get_db_connection() -> Iterator[sqlite3.Connection]:
    """
    Context manager for safe database connections.
    Handles connection, commit, rollback, and closing.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initializes the database and creates the sourcefiles table if it doesn't exist."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS sourcefiles (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                image_hash TEXT,
                thumbnail BLOB,
                exif_data BLOB
            )
        ''')
        c.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_image_hash ON sourcefiles(image_hash)
        ''')


def add_sourcefile(filename: str, image_hash: str, thumbnail: Optional[bytes], exif_data: Optional[bytes]) -> int:
    """Adds a new source file to the database and returns its ID."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO sourcefiles (filename, image_hash, thumbnail, exif_data)
            VALUES (?, ?, ?, ?)
        ''', (filename, image_hash, thumbnail, exif_data))
        last_id = c.lastrowid
        if last_id is None:
            raise sqlite3.Error("Could not retrieve last inserted ID.")
        return last_id


def get_sourcefile_by_id(sourcefile_id: int) -> Optional[SourceFile]:
    """Retrieves a source file by its ID."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, filename, image_hash, thumbnail, exif_data FROM sourcefiles WHERE id = ?', (sourcefile_id,))
        row = c.fetchone()
    if row:
        return SourceFile(
            id=row['id'],
            filename=row['filename'],
            image_hash=row['image_hash'],
            thumbnail=row['thumbnail'],
            exif_data=row['exif_data']
        )
    return None


def get_sourcefile_by_hash(image_hash: str) -> Optional[SourceFile]:
    """Retrieves a source file by its image hash."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, filename, image_hash, thumbnail, exif_data FROM sourcefiles WHERE image_hash = ?', (image_hash,))
        row = c.fetchone()
    if row:
        return SourceFile(
            id=row['id'],
            filename=row['filename'],
            image_hash=row['image_hash'],
            thumbnail=row['thumbnail'],
            exif_data=row['exif_data']
        )
    return None


def get_all_sourcefiles(limit: Optional[int] = None) -> List[SourceFile]:
    """Retrieves all source files from the database, newest first."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        query = 'SELECT id, filename, image_hash, thumbnail, exif_data FROM sourcefiles ORDER BY id DESC'
        params = []
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        c.execute(query, params)
        rows = c.fetchall()
    return [
        SourceFile(
            id=row['id'],
            filename=row['filename'],
            image_hash=row['image_hash'],
            thumbnail=row['thumbnail'],
            exif_data=row['exif_data']
        ) for row in rows
    ]


def update_sourcefile(sourcefile_id: int, filename: str, image_hash: str, thumbnail: Optional[bytes], exif_data: Optional[bytes]) -> bool:
    """Updates an existing source file."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE sourcefiles
            SET filename = ?, image_hash = ?, thumbnail = ?, exif_data = ?
            WHERE id = ?
        ''', (filename, image_hash, thumbnail, exif_data, sourcefile_id))
        return c.rowcount > 0


def delete_sourcefile(sourcefile_id: int) -> bool:
    """Deletes a source file from the database."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM sourcefiles WHERE id = ?', (sourcefile_id,))
        return c.rowcount > 0


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")
