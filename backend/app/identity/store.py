"""SQLite identity, session, and contact store."""
from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.domain.enums import UserRole
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.security import hash_password, token_hash, verify_password

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'professional',
    is_system INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    deleted_at REAL
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    deleted_at REAL,
    FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at REAL NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    company TEXT,
    website TEXT,
    job_title TEXT,
    message TEXT NOT NULL,
    user_id TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audits (
    analysis_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT,
    website_url TEXT,
    status TEXT,
    page_count INTEGER NOT NULL DEFAULT 0,
    overall_score REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""

PLANS = ("starter", "professional", "business", "enterprise")


def _now() -> float:
    return time.time()


class IdentityStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        user_cols = {row["name"] for row in self._query("PRAGMA table_info(users)")}
        if "last_login_at" not in user_cols:
            self._execute("ALTER TABLE users ADD COLUMN last_login_at REAL")
        if "auth_provider" not in user_cols:
            self._execute("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'")
        if "oauth_id" not in user_cols:
            self._execute("ALTER TABLE users ADD COLUMN oauth_id TEXT")
        if "avatar_url" not in user_cols:
            self._execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def _query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def _one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        rows = self._query(sql, params)
        return rows[0] if rows else None

    def seed_system(self) -> None:
        existing = self._one("SELECT org_id FROM organizations WHERE is_system = 1")
        if not existing:
            self._execute(
                "INSERT INTO organizations (org_id, name, slug, plan, is_system, is_active, created_at) VALUES (?, ?, ?, ?, 1, 1, ?)",
                ("org_system", "Dristik", "dristik", "enterprise", _now()),
            )
        email = (settings.SYSTEM_ADMIN_EMAIL or "admin@dristik.ai").strip().lower()
        full_name = (settings.SYSTEM_ADMIN_NAME or "Dristik Admin").strip()
        password = settings.SYSTEM_ADMIN_PASSWORD or "DristikAdmin1!"
        admin = self._one("SELECT * FROM users WHERE is_system = 1 AND deleted_at IS NULL")
        if not admin:
            self._execute(
                """INSERT INTO users (user_id, org_id, email, full_name, password_hash, role, is_active, is_system, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)""",
                (
                    "usr_system",
                    "org_system",
                    email,
                    full_name,
                    hash_password(password),
                    UserRole.SYSTEM_ADMIN.value,
                    _now(),
                ),
            )
            return
        # Do not overwrite existing admin password on reboot with default credentials
        custom_password_set = bool(settings.SYSTEM_ADMIN_PASSWORD and settings.SYSTEM_ADMIN_PASSWORD != "DristikAdmin1!")
        reset_pwd = getattr(settings, "RESET_SYSTEM_ADMIN_PASSWORD_ON_STARTUP", False) or (admin["email"] != email) or custom_password_set
        if reset_pwd:
            self._execute(
                """UPDATE users
                   SET email = ?, full_name = ?, password_hash = ?, is_active = 1, role = ?
                   WHERE user_id = ?""",
                (email, full_name, hash_password(password), UserRole.SYSTEM_ADMIN.value, admin["user_id"]),
            )
            self.revoke_user_sessions(admin["user_id"])
        else:
            self._execute(
                """UPDATE users
                   SET email = ?, full_name = ?, is_active = 1, role = ?
                   WHERE user_id = ?""",
                (email, full_name, UserRole.SYSTEM_ADMIN.value, admin["user_id"]),
            )

    def create_organization(self, name: str, slug: str, plan: str = "professional") -> Dict[str, Any]:
        org_id = f"org_{uuid.uuid4().hex[:10]}"
        self._execute(
            "INSERT INTO organizations (org_id, name, slug, plan, is_system, is_active, created_at) VALUES (?, ?, ?, ?, 0, 1, ?)",
            (org_id, name.strip(), slug, plan, _now()),
        )
        return {"org_id": org_id, "name": name.strip(), "slug": slug, "plan": plan}

    def slug_taken(self, slug: str) -> bool:
        return self._one("SELECT org_id FROM organizations WHERE slug = ?", (slug,)) is not None

    def email_taken(self, email: str) -> bool:
        row = self._one("SELECT user_id FROM users WHERE email = ? AND deleted_at IS NULL", (email.lower(),))
        return row is not None

    def create_user(
        self,
        org_id: str,
        email: str,
        full_name: str,
        password: str,
        role: UserRole,
        is_system: bool = False,
    ) -> UserIdentity:
        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        self._execute(
            """INSERT INTO users (user_id, org_id, email, full_name, password_hash, role, is_active, is_system, created_at, auth_provider)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 'local')""",
            (
                user_id,
                org_id,
                email.strip().lower(),
                full_name.strip(),
                hash_password(password),
                role.value,
                1 if is_system else 0,
                _now(),
            ),
        )
        identity = self.get_user(user_id)
        assert identity is not None
        return identity

    def create_oauth_user(
        self,
        org_id: str,
        email: str,
        full_name: str,
        provider: str,
        oauth_id: str,
        role: UserRole = UserRole.OWNER,
        avatar_url: Optional[str] = None,
    ) -> UserIdentity:
        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        # Secure placeholder password hash that cannot be matched by plain password auth
        placeholder_hash = f"oauth_{provider}_{uuid.uuid4().hex}"
        self._execute(
            """INSERT INTO users (user_id, org_id, email, full_name, password_hash, role, is_active, is_system, created_at, last_login_at, auth_provider, oauth_id, avatar_url)
               VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?)""",
            (
                user_id,
                org_id,
                email.strip().lower(),
                full_name.strip(),
                placeholder_hash,
                role.value,
                _now(),
                _now(),
                provider,
                str(oauth_id),
                avatar_url,
            ),
        )
        identity = self.get_user(user_id)
        assert identity is not None
        return identity

    def get_user_by_oauth(self, provider: str, oauth_id: str) -> Optional[UserIdentity]:
        row = self._one(
            "SELECT * FROM users WHERE auth_provider = ? AND oauth_id = ? AND deleted_at IS NULL",
            (provider, str(oauth_id)),
        )
        return self._identity(row) if row else None

    def link_oauth(
        self,
        user_id: str,
        provider: str,
        oauth_id: str,
        avatar_url: Optional[str] = None,
    ) -> Optional[UserIdentity]:
        self._execute(
            """UPDATE users
               SET auth_provider = ?, oauth_id = ?, avatar_url = COALESCE(?, avatar_url), last_login_at = ?
               WHERE user_id = ? AND deleted_at IS NULL""",
            (provider, str(oauth_id), avatar_url, _now(), user_id),
        )
        return self.get_user(user_id)

    def touch_login(self, user_id: str) -> None:
        self._execute("UPDATE users SET last_login_at = ? WHERE user_id = ?", (_now(), user_id))

    def _identity(self, row: sqlite3.Row) -> UserIdentity:
        org = self._one("SELECT name FROM organizations WHERE org_id = ?", (row["org_id"],))
        keys = row.keys()
        return UserIdentity(
            user_id=row["user_id"],
            org_id=row["org_id"],
            email=row["email"],
            full_name=row["full_name"],
            org_name=org["name"] if org else "",
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]) and row["deleted_at"] is None,
            is_system=bool(row["is_system"]),
            created_at=row["created_at"],
            last_login_at=row["last_login_at"] if "last_login_at" in keys else None,
            auth_provider=row["auth_provider"] if ("auth_provider" in keys and row["auth_provider"]) else "local",
            oauth_id=row["oauth_id"] if "oauth_id" in keys else None,
            avatar_url=row["avatar_url"] if "avatar_url" in keys else None,
        )

    def get_user(self, user_id: str) -> Optional[UserIdentity]:
        row = self._one("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self._identity(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[UserIdentity]:
        row = self._one("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL", (email.strip().lower(),))
        return self._identity(row) if row else None

    def authenticate(self, email: str, password: str) -> Optional[UserIdentity]:
        row = self._one("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL", (email.strip().lower(),))
        if not row or not row["is_active"]:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        self._execute("UPDATE users SET last_login_at = ? WHERE user_id = ?", (_now(), row["user_id"]))
        return self._identity(row)

    def verify_user_password(self, user_id: str, password: str) -> bool:
        row = self._one("SELECT password_hash FROM users WHERE user_id = ? AND deleted_at IS NULL", (user_id,))
        if not row:
            return False
        return verify_password(password, row["password_hash"])

    def set_password(self, user_id: str, password: str) -> None:
        self._execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(password), user_id),
        )

    def create_session(self, user_id: str, token: str, days: int) -> None:
        self._execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token_hash(token), user_id, _now() + days * 86400, _now()),
        )

    def user_from_session(self, token: str) -> Optional[UserIdentity]:
        row = self._one(
            "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?",
            (token_hash(token),),
        )
        if not row or row["expires_at"] < _now():
            if row:
                self._execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
            return None
        user = self.get_user(row["user_id"])
        if not user or not user.is_active:
            return None
        return user

    def revoke_session(self, token: str) -> None:
        self._execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))

    def revoke_user_sessions(self, user_id: str) -> None:
        self._execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def create_reset(self, user_id: str, token: str, hours: float = 1.0) -> None:
        self._execute(
            "INSERT INTO password_resets (token_hash, user_id, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
            (token_hash(token), user_id, _now() + hours * 3600, _now()),
        )

    def consume_reset(self, token: str) -> Optional[str]:
        row = self._one(
            "SELECT user_id, expires_at, used FROM password_resets WHERE token_hash = ?",
            (token_hash(token),),
        )
        if not row or row["used"] or row["expires_at"] < _now():
            return None
        self._execute("UPDATE password_resets SET used = 1 WHERE token_hash = ?", (token_hash(token),))
        return row["user_id"]

    def list_members(self, org_id: str) -> List[UserIdentity]:
        rows = self._query(
            "SELECT * FROM users WHERE org_id = ? AND deleted_at IS NULL ORDER BY created_at ASC",
            (org_id,),
        )
        return [self._identity(r) for r in rows]

    def update_role(self, user_id: str, role: UserRole) -> None:
        self._execute("UPDATE users SET role = ? WHERE user_id = ?", (role.value, user_id))

    def deactivate_user(self, user_id: str) -> None:
        self._execute(
            "UPDATE users SET is_active = 0, deleted_at = ? WHERE user_id = ?",
            (_now(), user_id),
        )
        self.revoke_user_sessions(user_id)

    def owner_count(self, org_id: str) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM users WHERE org_id = ? AND role = ? AND deleted_at IS NULL AND is_active = 1",
            (org_id, UserRole.OWNER.value),
        )
        return int(row["n"]) if row else 0

    def deactivate_org(self, org_id: str) -> None:
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found.")
        if org["is_system"]:
            raise ValueError("The Dristik system organization cannot be deleted.")
        self._execute(
            "UPDATE organizations SET is_active = 0, deleted_at = ? WHERE org_id = ?",
            (_now(), org_id),
        )
        members = self.list_members(org_id)
        for member in members:
            if member.is_system:
                continue
            self.deactivate_user(member.user_id)

    def list_organizations(self) -> List[Dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM organizations WHERE deleted_at IS NULL ORDER BY created_at DESC"
        )
        out = []
        for row in rows:
            count_row = self._one(
                "SELECT COUNT(*) AS n FROM users WHERE org_id = ? AND deleted_at IS NULL",
                (row["org_id"],),
            )
            out.append({
                "org_id": row["org_id"],
                "name": row["name"],
                "slug": row["slug"],
                "plan": row["plan"],
                "is_system": bool(row["is_system"]),
                "is_active": bool(row["is_active"]),
                "member_count": int(count_row["n"]) if count_row else 0,
                "created_at": row["created_at"],
            })
        return out

    def add_contact(self, payload: Dict[str, Any]) -> str:
        contact_id = f"ct_{uuid.uuid4().hex[:12]}"
        self._execute(
            """INSERT INTO contacts (contact_id, name, email, phone, company, website, job_title, message, user_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contact_id,
                payload["name"],
                payload["email"],
                payload.get("phone") or "",
                payload.get("company") or "",
                payload.get("website") or "",
                payload.get("job_title") or "",
                payload["message"],
                payload.get("user_id"),
                _now(),
            ),
        )
        return contact_id

    def list_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM contacts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def get_organization(self, org_id: str) -> Optional[sqlite3.Row]:
        return self._one("SELECT * FROM organizations WHERE org_id = ?", (org_id,))

    def set_org_plan(self, org_id: str, plan: str) -> None:
        if plan not in PLANS:
            raise ValueError("Plan must be starter, professional, business, or enterprise.")
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found.")
        self._execute("UPDATE organizations SET plan = ? WHERE org_id = ?", (plan, org_id))

    def set_org_active(self, org_id: str, active: bool) -> None:
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found.")
        if org["is_system"]:
            raise ValueError("The Dristik system organization cannot be deactivated.")
        if active:
            self._execute(
                "UPDATE organizations SET is_active = 1, deleted_at = NULL WHERE org_id = ?",
                (org_id,),
            )
            self._execute(
                "UPDATE users SET is_active = 1, deleted_at = NULL WHERE org_id = ? AND is_system = 0",
                (org_id,),
            )
            return
        self.deactivate_org(org_id)

    def purge_organization(self, org_id: str) -> None:
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found.")
        if org["is_system"]:
            raise ValueError("The Dristik system organization cannot be deleted.")
        user_ids = [r["user_id"] for r in self._query("SELECT user_id FROM users WHERE org_id = ?", (org_id,))]
        for user_id in user_ids:
            self._execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            self._execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM audits WHERE org_id = ?", (org_id,))
        self._execute("DELETE FROM users WHERE org_id = ?", (org_id,))
        self._execute("DELETE FROM organizations WHERE org_id = ?", (org_id,))

    def restore_user(self, user_id: str) -> None:
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found.")
        if user.is_system:
            raise ValueError("The Dristik system admin cannot be changed this way.")
        self._execute(
            "UPDATE users SET is_active = 1, deleted_at = NULL WHERE user_id = ?",
            (user_id,),
        )

    def record_audit(
        self,
        analysis_id: str,
        org_id: str,
        user_id: Optional[str],
        website_url: str,
        status: str,
        page_count: int = 0,
        overall_score: Optional[float] = None,
    ) -> None:
        now = _now()
        existing = self._one("SELECT analysis_id FROM audits WHERE analysis_id = ?", (analysis_id,))
        if existing:
            self._execute(
                """UPDATE audits SET status = ?, page_count = ?, overall_score = ?, updated_at = ?
                   WHERE analysis_id = ?""",
                (status, page_count, overall_score, now, analysis_id),
            )
            return
        self._execute(
            """INSERT INTO audits (analysis_id, org_id, user_id, website_url, status, page_count, overall_score, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (analysis_id, org_id, user_id, website_url, status, page_count, overall_score, now, now),
        )

    def expire_sessions(self) -> int:
        cur = self._execute("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
        return cur.rowcount if cur.rowcount is not None else 0

    def cleanup_resets(self) -> int:
        cur = self._execute(
            "DELETE FROM password_resets WHERE used = 1 OR expires_at < ?",
            (_now(),),
        )
        return cur.rowcount if cur.rowcount is not None else 0

    def vacuum(self) -> None:
        with self._lock:
            self._conn.execute("VACUUM")

    def db_stats(self) -> Dict[str, Any]:
        path = Path(self.path)
        size = path.stat().st_size if path.exists() else 0
        tables = {
            "organizations": self._one("SELECT COUNT(*) AS n FROM organizations")["n"],
            "users": self._one("SELECT COUNT(*) AS n FROM users")["n"],
            "sessions": self._one("SELECT COUNT(*) AS n FROM sessions")["n"],
            "password_resets": self._one("SELECT COUNT(*) AS n FROM password_resets")["n"],
            "contacts": self._one("SELECT COUNT(*) AS n FROM contacts")["n"],
            "audits": self._one("SELECT COUNT(*) AS n FROM audits")["n"],
        }
        live_sessions = self._one(
            "SELECT COUNT(*) AS n FROM sessions WHERE expires_at > ?",
            (_now(),),
        )["n"]
        return {
            "path": str(path),
            "size_bytes": size,
            "tables": tables,
            "live_sessions": int(live_sessions),
        }

    def platform_overview(self) -> Dict[str, Any]:
        now = _now()
        day, week, month = 86400, 7 * 86400, 30 * 86400

        def count(sql: str, params: tuple = ()) -> int:
            row = self._one(sql, params)
            return int(row["n"]) if row else 0

        orgs_active = count("SELECT COUNT(*) AS n FROM organizations WHERE is_active = 1 AND deleted_at IS NULL")
        orgs_deleted = count("SELECT COUNT(*) AS n FROM organizations WHERE deleted_at IS NOT NULL")
        users_active = count("SELECT COUNT(*) AS n FROM users WHERE is_active = 1 AND deleted_at IS NULL")
        users_deleted = count("SELECT COUNT(*) AS n FROM users WHERE deleted_at IS NOT NULL")
        customers = count(
            "SELECT COUNT(*) AS n FROM organizations WHERE is_system = 0 AND deleted_at IS NULL"
        )

        plan_rows = self._query(
            """SELECT plan, COUNT(*) AS n FROM organizations
               WHERE is_system = 0 AND deleted_at IS NULL
               GROUP BY plan"""
        )
        plan_mix = {name: 0 for name in PLANS}
        for row in plan_rows:
            plan_mix[row["plan"]] = int(row["n"])

        role_rows = self._query(
            """SELECT role, COUNT(*) AS n FROM users
               WHERE deleted_at IS NULL GROUP BY role"""
        )
        role_mix = {role.value: 0 for role in UserRole}
        for row in role_rows:
            role_mix[row["role"]] = int(row["n"])

        audits_total = count("SELECT COUNT(*) AS n FROM audits")
        audits_week = count("SELECT COUNT(*) AS n FROM audits WHERE created_at >= ?", (now - week,))
        contacts_total = count("SELECT COUNT(*) AS n FROM contacts")
        contacts_week = count("SELECT COUNT(*) AS n FROM contacts WHERE created_at >= ?", (now - week,))

        return {
            "generated_at": now,
            "organizations": {
                "total": orgs_active + orgs_deleted,
                "active": orgs_active,
                "deleted": orgs_deleted,
                "customer": customers,
                "system": count("SELECT COUNT(*) AS n FROM organizations WHERE is_system = 1"),
            },
            "users": {
                "total": users_active + users_deleted,
                "active": users_active,
                "deleted": users_deleted,
                "signed_up_24h": count(
                    "SELECT COUNT(*) AS n FROM users WHERE created_at >= ?", (now - day,)
                ),
                "signed_up_7d": count(
                    "SELECT COUNT(*) AS n FROM users WHERE created_at >= ?", (now - week,)
                ),
                "signed_up_30d": count(
                    "SELECT COUNT(*) AS n FROM users WHERE created_at >= ?", (now - month,)
                ),
                "logged_in_24h": count(
                    "SELECT COUNT(*) AS n FROM users WHERE last_login_at IS NOT NULL AND last_login_at >= ?",
                    (now - day,),
                ),
            },
            "plan_mix": plan_mix,
            "role_mix": role_mix,
            "audits": {
                "total": audits_total,
                "last_7d": audits_week,
                "last_30d": count("SELECT COUNT(*) AS n FROM audits WHERE created_at >= ?", (now - month,)),
            },
            "contacts": {"total": contacts_total, "last_7d": contacts_week},
            "database": self.db_stats(),
        }

    def organization_directory(self, include_deleted: bool = True) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM organizations ORDER BY is_system DESC, created_at DESC"
        if not include_deleted:
            sql = "SELECT * FROM organizations WHERE deleted_at IS NULL ORDER BY is_system DESC, created_at DESC"
        orgs = []
        for row in self._query(sql):
            orgs.append(self._org_detail(row))
        return orgs

    def _org_detail(self, row: sqlite3.Row) -> Dict[str, Any]:
        members = self._query("SELECT * FROM users WHERE org_id = ? ORDER BY created_at ASC", (row["org_id"],))
        role_mix = {role.value: 0 for role in UserRole}
        active_members = 0
        people = []
        for member in members:
            identity = self._identity(member)
            if identity.is_active:
                active_members += 1
                role_mix[identity.role.value] += 1
            people.append({
                "user_id": identity.user_id,
                "email": identity.email,
                "full_name": identity.full_name,
                "role": identity.role.value,
                "role_label": Authorizer.role_label(identity.role),
                "is_active": identity.is_active,
                "is_system": identity.is_system,
                "created_at": identity.created_at,
                "last_login_at": identity.last_login_at,
                "deleted_at": member["deleted_at"],
            })
        audits = self._query(
            "SELECT COUNT(*) AS n, AVG(overall_score) AS avg_score FROM audits WHERE org_id = ?",
            (row["org_id"],),
        )[0]
        return {
            "org_id": row["org_id"],
            "name": row["name"],
            "slug": row["slug"],
            "plan": row["plan"],
            "is_system": bool(row["is_system"]),
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "deleted_at": row["deleted_at"],
            "member_count": active_members,
            "member_total": len(members),
            "role_mix": role_mix,
            "audit_count": int(audits["n"] or 0),
            "avg_score": round(float(audits["avg_score"]), 1) if audits["avg_score"] is not None else None,
            "members": people,
        }


_store: Optional[IdentityStore] = None


def get_store() -> IdentityStore:
    global _store
    if _store is None:
        _store = IdentityStore(settings.AUTH_DATABASE_PATH)
        _store.seed_system()
    return _store


def reset_store(path: str) -> IdentityStore:
    global _store
    if _store is not None:
        try:
            _store.close()
        except Exception:
            pass
    _store = IdentityStore(path)
    _store.seed_system()
    return _store
