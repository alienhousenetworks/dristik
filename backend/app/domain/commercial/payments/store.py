"""
Dristik AI Payment & Entitlement Store
Persists orders, verified payment receipts, and audit entitlement vouchers.
Guarantees server-side validation for paid audit tiers and prevents fake voucher minting.
"""
import time
import uuid
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field

class OrderRecord(BaseModel):
    order_id: str
    plan_id: str
    plan_name: str
    amount_inr: int
    amount_paise: int
    currency: str = "INR"
    target_url: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    company_name: Optional[str] = None
    gstin: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    status: str = "created"  # created | paid | failed
    payment_id: Optional[str] = None
    signature: Optional[str] = None

class VoucherRecord(BaseModel):
    voucher_code: str
    order_id: str
    plan_id: str
    target_url: str
    payment_id: str
    max_pages: int
    created_at: float = Field(default_factory=time.time)
    redeemed_count: int = 0

class PaymentStore:
    """
    In-memory / persistent ledger of verified commercial orders and vouchers.
    Singleton accessible across API routes.
    """
    def __init__(self):
        self._orders: Dict[str, OrderRecord] = {}
        self._vouchers: Dict[str, VoucherRecord] = {}

    def save_order(self, order: OrderRecord) -> OrderRecord:
        self._orders[order.order_id] = order
        return order

    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        return self._orders.get(order_id)

    def mark_order_paid(self, order_id: str, payment_id: str, signature: str) -> Optional[OrderRecord]:
        order = self._orders.get(order_id)
        if order:
            order.status = "paid"
            order.payment_id = payment_id
            order.signature = signature
        return order

    def issue_voucher(
        self,
        order_id: str,
        plan_id: str,
        target_url: str,
        payment_id: str,
        max_pages: int
    ) -> VoucherRecord:
        # Generate clean standardized voucher code
        voucher_code = f"DRISTIK-{plan_id.upper()}-{uuid.uuid4().hex[:8].upper()}"
        rec = VoucherRecord(
            voucher_code=voucher_code,
            order_id=order_id,
            plan_id=plan_id,
            target_url=target_url,
            payment_id=payment_id,
            max_pages=max_pages
        )
        self._vouchers[voucher_code] = rec
        return rec

    def get_voucher(self, voucher_code: str) -> Optional[VoucherRecord]:
        return self._vouchers.get(voucher_code.strip().upper())

    def validate_entitlement(self, voucher_code: Optional[str], target_url: str, requested_pages: int) -> tuple[bool, str, int]:
        """
        Validates whether a voucher is legitimate and covers requested crawl depth.
        Returns: (is_valid, reason, allowed_pages)
        """
        if not voucher_code:
            return False, "No voucher code provided.", 1

        voucher = self.get_voucher(voucher_code)
        if not voucher:
            return False, f"Voucher '{voucher_code}' not found or invalid.", 1

        # Check domain/url match
        v_domain = voucher.target_url.replace("https://", "").replace("http://", "").split("/")[0].lower()
        t_domain = target_url.replace("https://", "").replace("http://", "").split("/")[0].lower()
        if v_domain and t_domain and v_domain != t_domain:
            return False, f"Voucher is issued for '{voucher.target_url}', not '{target_url}'.", 1

        if requested_pages > voucher.max_pages:
            return False, f"Voucher allows up to {voucher.max_pages} pages, but {requested_pages} were requested.", voucher.max_pages

        voucher.redeemed_count += 1
        return True, "Valid entitlement", voucher.max_pages

    def clear(self):
        """For testing purposes."""
        self._orders.clear()
        self._vouchers.clear()

_payment_store_instance = PaymentStore()
payment_store = _payment_store_instance

def get_payment_store() -> PaymentStore:
    return _payment_store_instance
