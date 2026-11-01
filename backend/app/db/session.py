"""
Unified Database Session & Engine Lifecycle Management.
Fail-fast connectivity without silent mock fallbacks.
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Any, Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import DristikException
import app.core.exceptions as _core_exceptions
from app.db.base import Base

logger = logging.getLogger(__name__)


class DatabaseConnectionError(DristikException, RuntimeError):
    """Raised when engine cannot establish connection or health check fails."""
    def __init__(
        self,
        message: str = "Database connection failed",
        status_code: int = 500,
    ):
        super().__init__(message, status_code=status_code)


# Register on app.core.exceptions for backward compatibility
_core_exceptions.DatabaseConnectionError = DatabaseConnectionError


def mask_database_url(url: Any) -> str:
    """Mask credentials in database URL for safe logging/diagnostics."""
    url_str = str(url)
    try:
        parsed = make_url(url_str)
        # If password contains unencoded '@', make_url misparses the suffix
        # into parsed.host
        if parsed.host and "@" in parsed.host:
            raise ValueError(
                "Host contains '@'; unencoded credential detected in authority"
            )
        return parsed.render_as_string(hide_password=True)
    except Exception:
        return re.sub(r"://([^:]+):([^/?#]*)@", r"://\1:***@", url_str)


def create_app_engine(url: Optional[Any] = None, **kwargs: Any):
    """Create and configure a production-grade SQLAlchemy engine."""
    default_url = "sqlite:///data/dristik.db"
    raw_url = url or getattr(settings, "DATABASE_URL", default_url)
    url_str = str(raw_url)
    is_sqlite = url_str.startswith("sqlite")

    pool_pre_ping = getattr(settings, "DB_POOL_PRE_PING", True)

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": pool_pre_ping,
        "future": True,
    }

    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if "///" in url_str and not url_str.startswith("sqlite:///:memory:"):
            db_file = url_str.split("///", 1)[1]
            if db_file and not db_file.startswith(":memory:"):
                try:
                    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
                except Exception as exc:
                    logger.warning(
                        "Could not auto-create directory for SQLite db %s: %s",
                        db_file,
                        exc,
                    )
    else:
        connect_timeout = int(getattr(settings, "DB_CONNECT_TIMEOUT", 5))
        engine_kwargs["connect_args"] = {"connect_timeout": connect_timeout}
        engine_kwargs["pool_size"] = getattr(settings, "DB_POOL_SIZE", 10)
        engine_kwargs["max_overflow"] = getattr(
            settings, "DB_MAX_OVERFLOW", 20
        )
        engine_kwargs["pool_timeout"] = getattr(
            settings, "DB_POOL_TIMEOUT", 30
        )
        engine_kwargs["pool_recycle"] = getattr(
            settings, "DB_POOL_RECYCLE", 1800
        )

    engine_kwargs.update(kwargs)
    return create_engine(raw_url, **engine_kwargs)


create_db_engine = create_app_engine

DATABASE_URL = getattr(settings, "DATABASE_URL", "sqlite:///data/dristik.db")
engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy Session.
    Ensures rollback on route error and guaranteed closure.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_database_connection(
    target_engine=None, timeout_seconds: float = 5.0
) -> bool:
    """
    Actively probe database connectivity using a lightweight query.
    Fails fast by raising DatabaseConnectionError if unreachable.
    Guarantees probe terminates within timeout_seconds even during
    TCP handshake. For SQLite engines, executes PRAGMA schema_version
    to validate physical disk header.
    """
    if isinstance(target_engine, (int, float)):
        timeout_seconds = float(target_engine)
        target_engine = None

    eng = target_engine or engine
    if eng is None:
        raise DatabaseConnectionError("Database engine is not configured.")

    masked = mask_database_url(str(eng.url))
    is_sqlite = getattr(eng, "name", "") == "sqlite"
    probe_query = (
        text("PRAGMA schema_version;") if is_sqlite else text("SELECT 1")
    )

    probe_result: dict[str, Any] = {"success": False, "error": None}

    def _probe_worker():
        try:
            with eng.connect() as conn:
                conn.execute(
                    probe_query.execution_options(timeout=timeout_seconds)
                )
            probe_result["success"] = True
        except Exception as exc:
            probe_result["error"] = exc

    probe_thread = threading.Thread(target=_probe_worker, daemon=True)
    probe_thread.start()
    probe_thread.join(timeout=timeout_seconds)

    if probe_thread.is_alive():
        logger.critical(
            "Database connectivity check timed out after %.1fs for %s",
            timeout_seconds,
            masked,
        )
        raise DatabaseConnectionError(
            f"Database connection timed out after {timeout_seconds}s "
            f"for {masked}"
        )

    if not probe_result["success"]:
        exc = probe_result["error"]
        logger.critical(
            "Database connectivity check failed for %s: %s", masked, exc
        )
        raise DatabaseConnectionError(
            f"Database connection failed for {masked}: {exc}"
        ) from exc

    logger.info(
        "Database connectivity successfully verified for %s", masked
    )
    return True


def init_db() -> None:
    """Create all tables defined on Base.metadata."""
    import app.db.models  # noqa: F401 # Register declarative models
    Base.metadata.create_all(bind=engine)
