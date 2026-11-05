import sys
import tempfile
import os
import shutil
from pathlib import Path
import sqlite3

backend_path = Path("/Users/sayantande/Downloads/dristik-main/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import (
    verify_database_connection,
    create_app_engine,
    DatabaseConnectionError
)

def test_sqlite_corruption_cases():
    print("=" * 80)
    print("TESTING SQLITE DATABASE CORRUPTION BOUNDARY CASES")
    print("=" * 80)
    
    cases = []
    
    # Case 1: 0-byte file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path_0byte = f.name
    cases.append(("0-Byte File", path_0byte, 0))
    
    # Case 2: 1-byte file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"\x00")
        path_1byte = f.name
    cases.append(("1-Byte File", path_1byte, 1))
    
    # Case 3: Truncated header (15 bytes)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"SQLite format 3") # 15 bytes, missing null terminator
        path_15byte = f.name
    cases.append(("Truncated Header (15 bytes)", path_15byte, 15))

    # Case 4: Truncated header (16 bytes magic only)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"SQLite format 3\x00") # 16 bytes magic only, header is 100 bytes
        path_16byte = f.name
    cases.append(("Truncated Header (16 bytes)", path_16byte, 16))

    # Case 5: Truncated header (50 bytes)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 34)
        path_50byte = f.name
    cases.append(("Truncated Header (50 bytes)", path_50byte, 50))

    # Case 6: Truncated header (99 bytes)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 83)
        path_99byte = f.name
    cases.append(("Truncated Header (99 bytes)", path_99byte, 99))

    # Case 7: 100 bytes of non-SQLite garbage
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"\xff" * 100)
        path_garbage = f.name
    cases.append(("100 Bytes Garbage Header", path_garbage, 100))

    # Case 8: Valid SQLite DB with Corrupted B-Tree (Malformed disk image)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path_valid = f.name
    conn = sqlite3.connect(path_valid)
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, payload TEXT);")
    conn.execute("INSERT INTO test_data VALUES (1, 'Initial record'), (2, 'Second record');")
    conn.commit()
    conn.close()
    
    with open(path_valid, "rb") as f:
        valid_bytes = bytearray(f.read())
    os.unlink(path_valid)
    
    # Keep 100-byte header intact, overwrite b-tree pages after byte 100 with garbage
    corrupt_btree_bytes = bytearray(valid_bytes)
    for i in range(100, len(corrupt_btree_bytes)):
        corrupt_btree_bytes[i] = 0xDE
        
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(corrupt_btree_bytes)
        path_corrupt_btree = f.name
    cases.append(("Corrupted B-Tree (Malformed Disk Image)", path_corrupt_btree, len(corrupt_btree_bytes)))

    # Case 9: Corrupted SQLite schema table (page 1 b-tree root corrupt)
    corrupt_schema_bytes = bytearray(valid_bytes)
    # Byte 100-108 is the b-tree page header of the schema table (page 1)
    for i in range(100, 108):
        corrupt_schema_bytes[i] = 0xFF
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(corrupt_schema_bytes)
        path_corrupt_schema = f.name
    cases.append(("Corrupted Schema B-Tree Root Page", path_corrupt_schema, len(corrupt_schema_bytes)))

    # Case 10: Non-existent SQLite file path in existing dir
    path_nonexistent = "/tmp/nonexistent_test_dristik_12345.db"
    if os.path.exists(path_nonexistent):
        os.unlink(path_nonexistent)
    cases.append(("Non-Existent File Path", path_nonexistent, -1))

    # Execute verify_database_connection for each case
    summary = []
    for name, filepath, size in cases:
        eng = create_app_engine(f"sqlite:///{filepath}")
        caught = False
        result = None
        error_msg = ""
        try:
            result = verify_database_connection(eng, timeout_seconds=1.0)
        except DatabaseConnectionError as exc:
            caught = True
            error_msg = str(exc)
        except Exception as exc:
            caught = True
            error_msg = f"Unexpected {type(exc).__name__}: {exc}"
            
        summary.append({
            "name": name,
            "filepath": filepath,
            "size": size,
            "caught_by_verify": caught,
            "result": result,
            "error_msg": error_msg
        })
        
        # Also check what actual sqlite3 operations do on this file
        sqlite_native_status = ""
        try:
            c = sqlite3.connect(filepath)
            cur = c.cursor()
            cur.execute("PRAGMA schema_version;")
            sv = cur.fetchall()
            cur.execute("SELECT * FROM sqlite_master;")
            sm = cur.fetchall()
            cur.execute("PRAGMA quick_check;")
            qc = cur.fetchall()
            sqlite_native_status = f"schema_version={sv}, sqlite_master={sm}, quick_check={qc}"
        except Exception as e:
            sqlite_native_status = f"{type(e).__name__}: {e}"
            
        print(f"[{'REJECTED' if caught else 'ACCEPTED'}] {name} (size: {size} bytes)")
        print(f"   verify_database_connection: caught={caught}, result={result}")
        if error_msg:
            print(f"   Error: {error_msg}")
        print(f"   Native SQLite query status: {sqlite_native_status}")
        print("-" * 60)

        # Cleanup temp file
        if os.path.exists(filepath):
            try:
                os.unlink(filepath)
            except OSError:
                pass

    print("=" * 80)
    print("CORRUPTION TEST MATRIX SUMMARY:")
    for item in summary:
        print(f"- {item['name']:<40}: verify_database_connection -> {'RAISED ERROR' if item['caught_by_verify'] else 'PASSED (ACCEPTED)'}")
    print("=" * 80)

if __name__ == "__main__":
    test_sqlite_corruption_cases()
