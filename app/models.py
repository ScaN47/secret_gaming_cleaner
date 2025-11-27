import sqlite3
import time
from pathlib import Path

# Create db directory if needed
db_dir = Path(__file__).parent / "db"
db_dir.mkdir(exist_ok=True)

DB_PATH = db_dir / "files.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        filename TEXT,
        stored_path TEXT,
        password TEXT,
        max_downloads INTEGER,
        downloads INTEGER DEFAULT 0,
        expire_ts INTEGER,
        created_ts INTEGER
    )
    ''')
    conn.commit()
    conn.close()

def insert_file(meta):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        INSERT INTO files (id, filename, stored_path, password, max_downloads, downloads, expire_ts, created_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (meta['id'], meta['filename'], meta['stored_path'], meta['password'],
          meta['max_downloads'], 0, meta['expire_ts'], int(time.time())))
    conn.commit()
    conn.close()

def get_file(id_):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT id, filename, stored_path, password, max_downloads, downloads, expire_ts FROM files WHERE id=?', (id_,))
    r = c.fetchone()
    conn.close()
    if not r: return None
    keys = ['id','filename','stored_path','password','max_downloads','downloads','expire_ts']
    return dict(zip(keys, r))

def increment_download(id_):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('UPDATE files SET downloads = downloads + 1 WHERE id=?', (id_,))
    conn.commit()
    conn.close()

def delete_file_record(id_):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('DELETE FROM files WHERE id=?', (id_,))
    conn.commit()
    conn.close()

def get_all_files():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT id, filename, stored_path, password, max_downloads, downloads, expire_ts, created_ts FROM files')
    records = c.fetchall()
    conn.close()
    result = []
    keys = ['id','filename','stored_path','password','max_downloads','downloads','expire_ts','created_ts']
    for r in records:
        result.append(dict(zip(keys, r)))
    return result
