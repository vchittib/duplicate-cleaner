"""Shared utilities for duplicate-cleaner."""

import hashlib
import sqlite3
import os
from pathlib import Path

DB_NAME = ".duplicate_cleaner_cache.db"


def format_size(num_bytes):
    """Format a byte count into a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def hash_file(path, chunk_size=65536):
    """Return SHA-256 hex digest of a file, or None on error."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


class HashCache:
    """SQLite-backed cache that maps (path, size, mtime) to a SHA-256 hash.

    If a file's size and mtime haven't changed, the cached hash is reused
    instead of re-reading the entire file.
    """

    def __init__(self, scan_dir):
        db_path = Path(scan_dir) / DB_NAME
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS hashes ("
            "  path TEXT PRIMARY KEY,"
            "  size INTEGER,"
            "  mtime REAL,"
            "  hash TEXT"
            ")"
        )
        self._conn.commit()

    def get(self, path):
        """Return cached hash if the file hasn't changed, else compute, store, and return it."""
        path = Path(path)
        try:
            stat = path.stat()
        except (PermissionError, OSError):
            return None

        row = self._conn.execute(
            "SELECT size, mtime, hash FROM hashes WHERE path = ?",
            (str(path),),
        ).fetchone()

        if row and row[0] == stat.st_size and row[1] == stat.st_mtime:
            return row[2]

        digest = hash_file(path)
        if digest:
            self._conn.execute(
                "INSERT OR REPLACE INTO hashes (path, size, mtime, hash) VALUES (?, ?, ?, ?)",
                (str(path), stat.st_size, stat.st_mtime, digest),
            )
            self._conn.commit()
        return digest

    def close(self):
        self._conn.close()
