import os
import sqlite3
from typing import Generator, Any
from app.db.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dristik.db")

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    def init_db():
        Base.metadata.create_all(bind=engine)

except ImportError:
    # Lightweight SQLite fallback
    class MockSession:
        def __init__(self):
            db_path = "dristik.db" if "sqlite:///" not in DATABASE_URL else DATABASE_URL.replace("sqlite:///", "")
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        def query(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return None
        def all(self):
            return []
        def order_by(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def offset(self, *args, **kwargs):
            return self
        def add(self, obj):
            pass
        def commit(self):
            self.conn.commit()
        def refresh(self, obj):
            pass
        def close(self):
            self.conn.close()

    Session = MockSession
    engine = None
    SessionLocal = MockSession

    def get_db():
        db = MockSession()
        try:
            yield db
        finally:
            db.close()

    def init_db():
        conn = sqlite3.connect("dristik.db")
        conn.execute("CREATE TABLE IF NOT EXISTS system_init (id INTEGER PRIMARY KEY, initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()
        conn.close()
