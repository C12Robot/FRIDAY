"""
FRIDAY - File System Master (Phase 17)
Indexes, searches, opens, and organizes files using SQLite + fuzzy search
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from fuzzywuzzy import fuzz, process

# ─────────────────────────────────────────────
# CONFIG — folders FRIDAY will index
# ─────────────────────────────────────────────
INDEXED_FOLDERS = [
    r"C:\\",  # Entire laptop
]

# Skip Windows system junk — speeds up indexing massively
SKIP_FOLDERS = {
    "Windows", "System32", "SysWOW64", "WinSxS",
    "Program Files", "Program Files (x86)",
    "ProgramData", "$Recycle.Bin", "AppData",
    "venv", "__pycache__", "node_modules", ".git"
}

DB_PATH = r"C:\Users\meena\Documents\ARIA\friday_files.db"

# File types FRIDAY cares about (skip junk)
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".html", ".css",     # code
    ".pdf", ".docx", ".txt", ".md",           # documents
    ".xlsx", ".csv", ".json",                 # data
    ".mp3", ".wav", ".mp4",                   # media
    ".png", ".jpg", ".jpeg",                  # images
    ".zip", ".tar",                           # archives
}

# ─────────────────────────────────────────────
# DATABASE SETUP
# Why SQLite? Fast, local, no server needed.
# Stores file path, name, size, modified date.
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            path TEXT UNIQUE,
            extension TEXT,
            size_kb REAL,
            modified TEXT,
            folder TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("[FRIDAY] File database initialized.")


# ─────────────────────────────────────────────
# INDEXER
# Walks every folder, stores file metadata in DB.
# UNIQUE on path — won't duplicate on re-index.
# ─────────────────────────────────────────────
def index_files():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    total = 0

    for folder in INDEXED_FOLDERS:
        if not os.path.exists(folder):
            print(f"[FRIDAY] Folder not found, skipping: {folder}")
            continue

        for root, dirs, files in os.walk(folder):
            # Skip system/hidden/junk folders
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in SKIP_FOLDERS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                try:
                    stats = os.stat(full_path)
                    size_kb = round(stats.st_size / 1024, 2)
                    modified = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")

                    cursor.execute("""
                        INSERT OR REPLACE INTO files (name, path, extension, size_kb, modified, folder)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (file, full_path, ext, size_kb, modified, root))
                    total += 1
                except Exception as e:
                    pass  # Skip files we can't access

    conn.commit()
    conn.close()
    print(f"[FRIDAY] Indexed {total} files.")
    return total


# ─────────────────────────────────────────────
# SEARCH
# Two modes:
#   1. Exact/fuzzy by filename
#   2. Filter by extension or folder
# fuzzywuzzy gives similarity score 0-100.
# We return matches above threshold (60+).
# ─────────────────────────────────────────────
def search_files(query, extension=None, limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if extension:
        cursor.execute("SELECT name, path, size_kb, modified FROM files WHERE extension = ?", (extension,))
    else:
        cursor.execute("SELECT name, path, size_kb, modified FROM files")

    all_files = cursor.fetchall()
    conn.close()

    if not all_files:
        return []

    # Fuzzy match query against all filenames
    names = [f[0] for f in all_files]
    matches = process.extract(query, names, scorer=fuzz.partial_ratio, limit=limit)

    results = []
    seen_paths = set()
    for match_name, score in matches:
        if score >= 60:
            for f in all_files:
                if f[0] == match_name and f[1] not in seen_paths:
                    seen_paths.add(f[1])
                    results.append({
                        "name": f[0],
                        "path": f[1],
                        "size_kb": f[2],
                        "modified": f[3],
                        "score": score
                    })
                    break

    return results


# ─────────────────────────────────────────────
# OPEN FILE
# Uses Windows 'start' command — opens with
# default app (same as double-clicking).
# ─────────────────────────────────────────────
def open_file(path):
    if not os.path.exists(path):
        print(f"[DEBUG] Path does not exist: '{path}'")
        return f"[FRIDAY] File not found: {path}"
    try:
        os.startfile(path)
        print(f"[DEBUG] os.startfile succeeded")
        return f"[FRIDAY] Opened: {path}"
    except Exception as e:
        print(f"[DEBUG] os.startfile failed: {e}")
        try:
            subprocess.Popen(['explorer', path])
            return f"Opened via explorer: {path}"
        except Exception as e2:
            return f"Failed: {e2}"
        


# ─────────────────────────────────────────────
# OPEN FOLDER
# Opens the folder containing a file in Explorer
# ─────────────────────────────────────────────
def open_folder(path):
    folder = os.path.dirname(path) if os.path.isfile(path) else path
    subprocess.Popen(f'explorer "{folder}"')
    return f"[FRIDAY] Opened folder: {folder}"


# ─────────────────────────────────────────────
# RENAME FILE
# Always confirms before renaming.
# ─────────────────────────────────────────────
def rename_file(old_path, new_name, confirmed=False):
    if not os.path.exists(old_path):
        return f"[FRIDAY] File not found: {old_path}"

    folder = os.path.dirname(old_path)
    new_path = os.path.join(folder, new_name)

    if not confirmed:
        return f"[FRIDAY] Confirm rename '{os.path.basename(old_path)}' → '{new_name}'? (yes/no)"

    try:
        os.rename(old_path, new_path)
        # Update DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET name = ?, path = ? WHERE path = ?", (new_name, new_path, old_path))
        conn.commit()
        conn.close()
        return f"[FRIDAY] Renamed to: {new_name}"
    except Exception as e:
        return f"[FRIDAY] Rename failed: {e}"


# ─────────────────────────────────────────────
# GET STATS
# How many files indexed, by type
# ─────────────────────────────────────────────
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM files")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT extension, COUNT(*) FROM files GROUP BY extension ORDER BY COUNT(*) DESC")
    by_type = cursor.fetchall()
    conn.close()
    return {"total": total, "by_type": by_type}


# ─────────────────────────────────────────────
# MAIN — test it directly
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== FRIDAY File System Master ===")
    init_db()

    print("\nIndexing your files... (first run may take 30-60 seconds)")
    total = index_files()

    stats = get_stats()
    print(f"\nTotal files indexed: {stats['total']}")
    print("Top file types:")
    for ext, count in stats['by_type'][:5]:
        print(f"  {ext}: {count} files")

    print("\n--- Test Search ---")
    query = input("Search for a file: ")
    results = search_files(query)
    if results:
        for r in results:
            print(f"  [{r['score']}%] {r['name']} — {r['path']}")
    else:
        print("No matches found.")