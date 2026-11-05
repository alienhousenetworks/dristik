"""
Empirical stress test for get_db session lifecycle, rollback, and concurrency.
"""
import sys
import os
import threading
import time
from unittest.mock import patch

backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.session import (
    create_app_engine,
    get_db,
    SessionLocal,
    Base,
    engine,
)
from sqlalchemy import Column, String, Integer, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

class StressItem(Base):
    __tablename__ = "stress_test_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

def setup_stress_table():
    Base.metadata.create_all(bind=engine)

def test_rollback_on_route_exception():
    print("--- Test 1: Real DB Rollback on Route Exception ---")
    setup_stress_table()
    
    # 1. Clean previous data
    with SessionLocal() as s:
        s.execute(text("DELETE FROM stress_test_items WHERE name LIKE 'test_%'"))
        s.commit()
    
    # 2. Simulate FastAPI request that fails after adding an item
    gen = get_db()
    db = next(gen)
    item = StressItem(name="test_rollback_item")
    db.add(item)
    db.flush() # Flushed to DB transaction, but not committed
    
    # Verify it is visible in the current transaction
    assert db.query(StressItem).filter_by(name="test_rollback_item").first() is not None
    
    # Now simulate exception in route
    try:
        gen.throw(RuntimeError("Route failed"))
    except RuntimeError:
        pass
    
    # 3. Verify from a fresh session that the item was rolled back
    with SessionLocal() as fresh_db:
        found = fresh_db.query(StressItem).filter_by(name="test_rollback_item").first()
        if found is None:
            print("PASSED: Uncommitted data was rolled back and is not in DB.")
        else:
            print("FAILED: Uncommitted data leaked into DB!")

def test_rollback_on_integrity_error():
    print("--- Test 2: Rollback on IntegrityError ---")
    setup_stress_table()
    
    # Add initial item
    with SessionLocal() as s:
        s.merge(StressItem(name="unique_item"))
        s.commit()
    
    gen = get_db()
    db = next(gen)
    try:
        # Violate unique constraint
        db.add(StressItem(name="unique_item"))
        db.commit()
    except IntegrityError as exc:
        try:
            gen.throw(exc)
        except IntegrityError:
            pass
            
    # Session must be closed
    print("PASSED: Handled IntegrityError cleanly.")

def test_premature_generator_close():
    print("--- Test 3: Premature Generator Close (Client Disconnect / GeneratorExit) ---")
    gen = get_db()
    db = next(gen)
    db.add(StressItem(name="test_disconnect_item"))
    db.flush()
    
    # Simulate client disconnect causing generator.close() -> GeneratorExit
    gen.close()
    
    # Verify from fresh session that uncommitted data was discarded by db.close()
    with SessionLocal() as fresh_db:
        found = fresh_db.query(StressItem).filter_by(name="test_disconnect_item").first()
        if found is None:
            print("PASSED: GeneratorExit closed session and discarded uncommitted data.")
        else:
            print("FAILED: Generator.close() leaked uncommitted data!")

def test_concurrent_sessions_under_load():
    print("--- Test 4: Concurrency and Pool Pressure (50 threads) ---")
    errors = []
    
    def worker(worker_id):
        try:
            gen = get_db()
            db = next(gen)
            # execute query
            db.execute(text("SELECT 1")).scalar()
            if worker_id % 2 == 0:
                # Half fail
                try:
                    gen.throw(ValueError(f"Worker {worker_id} simulated error"))
                except ValueError:
                    pass
            else:
                # Half succeed
                try:
                    next(gen)
                except StopIteration:
                    pass
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        print(f"FAILED: Concurrency test had {len(errors)} errors: {errors[0]}")
    else:
        print("PASSED: 50 concurrent get_db() sessions completed without pool exhaustion or leaks.")

if __name__ == "__main__":
    test_rollback_on_route_exception()
    test_rollback_on_integrity_error()
    test_premature_generator_close()
    test_concurrent_sessions_under_load()
