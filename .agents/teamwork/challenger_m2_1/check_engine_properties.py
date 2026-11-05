"""
Test create_app_engine pool_pre_ping and check_same_thread configurations.
"""
import sys
import os

backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.session import create_app_engine
from sqlalchemy.pool import SingletonThreadPool, StaticPool, QueuePool, NullPool

def check_engine(name, url):
    eng = create_app_engine(url)
    print(f"=== Engine: {name} ({url}) ===")
    print(f"Dialect: {eng.dialect.name}")
    print(f"Pool type: {type(eng.pool).__name__}")
    print(f"Pool pre_ping attr: {getattr(eng.pool, '_pre_ping', 'NOT_FOUND')}")
    # Check connect_args check_same_thread
    connect_args = getattr(eng.dialect, "connect_args", {})
    # For SQLite, check if check_same_thread was passed to creator/dbapi
    print(f"URL: {eng.url}")
    # Let's see if check_same_thread=False actually allows multithreaded sqlite access!
    return eng

if __name__ == "__main__":
    check_engine("SQLite memory", "sqlite:///:memory:")
    check_engine("SQLite file", "sqlite:///data/test.db")
    check_engine("Postgres", "postgresql://user:pass@localhost:5432/dristik")
