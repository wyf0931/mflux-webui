from tinydb import TinyDB, Query
from pathlib import Path
from datetime import datetime
import json

# Database directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# TinyDB database file
DB_FILE = DATA_DIR / "db.json"

# Initialize TinyDB
db = TinyDB(DB_FILE, ensure_ascii=False, indent=2)

# Tables
history_table = db.table('history')
settings_table = db.table('settings')

# History operations
def add_history_entry(entry):
    """Add a history entry (maintains max 100)"""
    history_table.insert(entry)
    # Trim to 100 entries (keep newest)
    all_entries = history_table.all()
    if len(all_entries) > 100:
        # Sort by timestamp descending, keep first 100
        all_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        to_keep = all_entries[:100]
        to_remove = all_entries[100:]
        for entry in to_remove:
            history_table.remove(doc_ids=[entry.doc_id])
        # Re-insert in correct order
        history_table.truncate()
        history_table.insert_multiple(to_keep)

def get_all_history():
    """Get all history entries, sorted by timestamp desc"""
    return sorted(history_table.all(), key=lambda x: x['timestamp'], reverse=True)

def get_history_by_timestamp(timestamp):
    """Get a history entry by timestamp"""
    Q = Query()
    return history_table.get(Q.timestamp == timestamp)

def delete_history(timestamp):
    """Delete a history entry by timestamp"""
    Q = Query()
    return history_table.remove(Q.timestamp == timestamp)

def clean_history():
    """Remove history entries with missing image files"""
    all_entries = get_all_history()
    valid_entries = [e for e in all_entries if Path(e['image_path']).exists()]
    history_table.truncate()
    history_table.insert_multiple(valid_entries)

# Settings operations
DEFAULT_SETTINGS = {
    'ollamaUrl': 'http://127.0.0.1:11434'
}

def get_settings():
    """Get all settings"""
    if len(settings_table) == 0:
        settings_table.insert(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()
    return settings_table.all()[0]

def update_settings(updates):
    """Update settings"""
    if settings_table.count() == 0:
        settings_table.insert({**DEFAULT_SETTINGS, **updates})
    else:
        Q = Query()
        settings_table.update(updates)
    return get_settings()

def get_setting(key, default=None):
    """Get a specific setting value"""
    settings = get_settings()
    return settings.get(key, default)

def set_setting(key, value):
    """Set a specific setting value"""
    return update_settings({key: value})
