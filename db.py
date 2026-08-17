from tinydb import TinyDB, Query
from pathlib import Path
import json
import threading

# Database directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# TinyDB database file
DB_FILE = DATA_DIR / "db.json"

# Thread lock for database access
_db_lock = threading.Lock()

def _get_db():
    """Get TinyDB instance with proper initialization."""
    return TinyDB(DB_FILE, ensure_ascii=False, indent=2)

def _ensure_db_file():
    """Ensure database file exists and is valid JSON."""
    if not DB_FILE.exists():
        DB_FILE.write_text('{}')
    else:
        try:
            content = DB_FILE.read_text()
            if not content.strip():
                DB_FILE.write_text('{}')
            else:
                json.loads(content)  # Validate JSON
        except json.JSONDecodeError:
            # Corrupted file, reset it
            DB_FILE.write_text('{}')

# Ensure db file is valid before any operations
_ensure_db_file()

# History operations
def add_history_entry(entry):
    """Add a history entry (maintains max 100)"""
    with _db_lock:
        db = _get_db()
        try:
            history_table = db.table('history')
            history_table.insert(entry)
            # Trim to 100 entries (keep newest)
            all_entries = history_table.all()
            if len(all_entries) > 100:
                all_entries.sort(key=lambda x: x['timestamp'], reverse=True)
                to_keep = all_entries[:100]
                history_table.truncate()
                history_table.insert_multiple(to_keep)
        finally:
            db.close()

def get_all_history():
    """Get all history entries, sorted by timestamp desc"""
    with _db_lock:
        db = _get_db()
        try:
            history_table = db.table('history')
            entries = history_table.all()
            return sorted(entries, key=lambda x: x['timestamp'], reverse=True)
        finally:
            db.close()

def get_history_by_timestamp(timestamp):
    """Get a history entry by timestamp"""
    with _db_lock:
        db = _get_db()
        try:
            history_table = db.table('history')
            Q = Query()
            return history_table.get(Q.timestamp == timestamp)
        finally:
            db.close()

def delete_history(timestamp):
    """Delete a history entry by timestamp"""
    with _db_lock:
        db = _get_db()
        try:
            history_table = db.table('history')
            Q = Query()
            return history_table.remove(Q.timestamp == timestamp)
        finally:
            db.close()

def clean_history():
    """Remove history entries with missing image files"""
    with _db_lock:
        db = _get_db()
        try:
            history_table = db.table('history')
            all_entries = history_table.all()
            valid_entries = [e for e in all_entries if Path(e.get('image_path', '')).exists()]
            history_table.truncate()
            history_table.insert_multiple(valid_entries)
        finally:
            db.close()
