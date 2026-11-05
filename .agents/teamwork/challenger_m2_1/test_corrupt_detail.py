import sqlite3
import tempfile
import os

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    f.write(b"GARBAGE_DATA_NOT_A_VALID_SQLITE_HEADER_1234567890" * 100)
    path = f.name

try:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    print("Executing SELECT 1:")
    cur.execute("SELECT 1")
    print("SELECT 1 result:", cur.fetchone())
    print("Executing SELECT count(*) FROM sqlite_master:")
    try:
        cur.execute("SELECT count(*) FROM sqlite_master")
        print("sqlite_master result:", cur.fetchone())
    except Exception as e:
        print("sqlite_master failed with:", type(e), e)
finally:
    os.unlink(path)
