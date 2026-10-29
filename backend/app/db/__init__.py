"""Dristik Relational Database and Content-Addressable Storage Layer."""
from app.db.base import Base
from app.db.session import get_db, SessionLocal
from app.db.storage_cas import ContentAddressableStorage

CASStorage = ContentAddressableStorage

__all__ = ["Base", "SessionLocal", "get_db", "ContentAddressableStorage", "CASStorage"]
