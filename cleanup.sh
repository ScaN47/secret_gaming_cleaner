#!/bin/bash
# запускать по cron раз в час
python3 - <<'PY'
import sqlite3, time, os
db = 'app/files.db'
conn = sqlite3.connect(db)
c = conn.cursor()
now = int(time.time())
c.execute('SELECT id, stored_path FROM files WHERE expire_ts IS NOT NULL AND expire_ts < ?', (now,))
rows = c.fetchall()
for id_, path in rows:
    try:
        os.remove(path)
    except:
        pass
    c.execute('DELETE FROM files WHERE id=?', (id_,))
conn.commit()
conn.close()
PY
