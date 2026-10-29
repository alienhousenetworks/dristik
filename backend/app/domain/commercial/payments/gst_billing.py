"""GST on checkout.

The live catalog does not add GST to the plan price. A GSTIN can be stored on
the order. It does not change the charged amount.
"""
GST_RATE = 0.0


def gst_amount_inr(base_inr: int, gstin: str | None = None) -> int:
    del base_inr, gstin
    return 0
