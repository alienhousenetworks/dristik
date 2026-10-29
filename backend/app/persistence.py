"""
Compatibility re-export from app.db.
Database models, repositories, and CAS storage are consolidated into backend/app/db/.
"""
from __future__ import annotations

import sys

__path__: list[str] = []

from app.db import storage_cas, enterprise_schema, schema, repository
from app.db import models, repositories
from app.db.storage_cas import ContentAddressableStorage, CASStorage

sys.modules["app.persistence.storage_cas"] = storage_cas
sys.modules["app.persistence.enterprise_schema"] = enterprise_schema
sys.modules["app.persistence.schema"] = schema
sys.modules["app.persistence.repository"] = repository
sys.modules["app.persistence.models"] = models
sys.modules["app.persistence.repositories"] = repositories

__all__ = [
    "ContentAddressableStorage",
    "CASStorage",
    "storage_cas",
    "enterprise_schema",
    "schema",
    "repository",
    "models",
    "repositories",
]
