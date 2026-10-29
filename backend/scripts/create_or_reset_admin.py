#!/usr/bin/env python3
"""
CLI script to create or update an Admin user in Dristik AI.

Usage:
    python scripts/create_or_reset_admin.py --email admin@dristik.ai --password "A@admin123456"
"""
import argparse
import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.domain.enums import UserRole
from app.identity.security import hash_password, password_errors
from app.identity.store import get_store, _now


def create_or_reset_admin(email: str, password: str, full_name: str = "Dristik Admin") -> None:
    email = email.strip().lower()
    full_name = full_name.strip()

    err = password_errors(password)
    if err:
        print(f"[-] Error: Password does not meet security requirements: {err}")
        sys.exit(1)

    store = get_store()

    # Ensure system organization exists
    system_org = store._one("SELECT org_id FROM organizations WHERE is_system = 1")
    if not system_org:
        store._execute(
            "INSERT INTO organizations (org_id, name, slug, plan, is_system, is_active, created_at) VALUES (?, ?, ?, ?, 1, 1, ?)",
            ("org_system", "Dristik", "dristik", "enterprise", _now()),
        )
        system_org_id = "org_system"
    else:
        system_org_id = system_org["org_id"]

    # Check if a user with this email already exists
    user = store._one("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL", (email,))
    pwd_hash = hash_password(password)

    if user:
        # Update existing user to System Admin with the new password
        store._execute(
            """UPDATE users
               SET full_name = ?, password_hash = ?, role = ?, is_active = 1, is_system = 1
               WHERE user_id = ?""",
            (full_name, pwd_hash, UserRole.SYSTEM_ADMIN.value, user["user_id"]),
        )
        store.revoke_user_sessions(user["user_id"])
        print(f"[+] Successfully updated existing user '{email}' (ID: {user['user_id']}) to System Admin!")
    else:
        # Check if default usr_system exists
        system_user = store._one("SELECT * FROM users WHERE is_system = 1 AND deleted_at IS NULL")
        if system_user:
            store._execute(
                """UPDATE users
                   SET email = ?, full_name = ?, password_hash = ?, role = ?, is_active = 1
                   WHERE user_id = ?""",
                (email, full_name, pwd_hash, UserRole.SYSTEM_ADMIN.value, system_user["user_id"]),
            )
            store.revoke_user_sessions(system_user["user_id"])
            print(f"[+] Successfully updated System Admin user (ID: {system_user['user_id']}) with email '{email}'!")
        else:
            new_user_id = "usr_system"
            store._execute(
                """INSERT INTO users (user_id, org_id, email, full_name, password_hash, role, is_active, is_system, created_at, auth_provider)
                   VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, 'local')""",
                (new_user_id, system_org_id, email, full_name, pwd_hash, UserRole.SYSTEM_ADMIN.value, _now()),
            )
            print(f"[+] Successfully created new System Admin user '{email}' (ID: {new_user_id})!")

    print(f"[✓] Credentials confirmed:")
    print(f"    - Email:    {email}")
    print(f"    - Password: {password}")
    print(f"    - Role:     {UserRole.SYSTEM_ADMIN.value}")


def main():
    parser = argparse.ArgumentParser(description="Create or reset Dristik AI Admin user credentials.")
    parser.add_argument("--email", default="admin@dristik.ai", help="Admin email address (default: admin@dristik.ai)")
    parser.add_argument("--password", default="A@admin123456", help="Admin password (default: A@admin123456)")
    parser.add_argument("--name", default="Dristik Admin", help="Admin display name (default: Dristik Admin)")

    args = parser.parse_args()
    create_or_reset_admin(email=args.email, password=args.password, full_name=args.name)


if __name__ == "__main__":
    main()
