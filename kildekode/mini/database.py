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
                thumbnail BLOB,
                exif_data BLOB
            )
        ''')


def add_sourcefile(filename: str, thumbnail: Optional[bytes], exif_data: Optional[bytes]) -> int:
    """Adds a new source file to the database and returns its ID."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO sourcefiles (filename, thumbnail, exif_data)
            VALUES (?, ?, ?)
        ''', (filename, thumbnail, exif_data))
        # Return lastrowid from the connection and ignore the type checker error
                # Return lastrowid from the cursor and ignore the type checker error
        c.execute('''
            INSERT INTO sourcefiles (filename, thumbnail, exif_data)
            VALUES (?, ?, ?)
        ''', (filename, thumbnail, exif_data))
        # Return lastrowid from the cursor
        return c.lastrowid


def get_sourcefile_by_id(sourcefile_id: int) -> Optional[SourceFile]:
    """Retrieves a source file by its ID."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, filename, thumbnail, exif_data FROM sourcefiles WHERE id = ?', (sourcefile_id,))
        row = c.fetchone()
    if row:
        return SourceFile(id=row[0], filename=row[1], thumbnail=row[2], exif_data=row[3])
    return None


def get_all_sourcefiles() -> List[SourceFile]:
    """Retrieval all source files from the database."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, filename, thumbnail, exif_data FROM sourcefiles')
        rows = c.fetchall()
    return [SourceFile(id=row[0], filename=row[1], thumbnail=row[2], exif_data=row[3]) for row in rows]


def update_sourcefile(sourcefile_id: int, filename: str, thumbnail: Optional[bytes], exif_data: Optional[bytes]) -> bool:
    """Updates an existing source file."""
    with _get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE sourcefiles
            SET filename = ?, thumbnail = ?, exif_data = ?
            WHERE id = ?
        ''', (filename, thumbnail, exif_data, sourcefile_id))
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
