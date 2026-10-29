"""Public contact form and system inbox."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional, require_permission
from app.identity.service import EMAIL_RE
from app.identity.store import get_store

router = APIRouter(prefix="/contact", tags=["Contact"])


class ContactBody(BaseModel):
    name: str
    email: str
    phone: str = ""
    company: str = ""
    website: str = ""
    job_title: str = ""
    message: str = Field(min_length=8)


@router.post("")
def submit_contact(
    body: ContactBody,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    name = body.name.strip()
    email = body.email.strip().lower()
    message = body.message.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Enter your name.")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(message) < 8:
        raise HTTPException(status_code=400, detail="Enter a short message.")
    contact_id = get_store().add_contact({
        "name": name,
        "email": email,
        "phone": body.phone.strip(),
        "company": body.company.strip(),
        "website": body.website.strip(),
        "job_title": body.job_title.strip(),
        "message": message,
        "user_id": user.user_id if user else None,
    })
    return {
        "ok": True,
        "contact_id": contact_id,
        "message": "Thanks. The Dristik team will get back to you.",
    }


@router.get("")
def list_contacts(user: UserIdentity = Depends(require_permission("contact:read"))):
    return {"contacts": get_store().list_contacts()}
