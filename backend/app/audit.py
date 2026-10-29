"""Compatibility shim for migrated audit packages (transferred to app.crawl.audit)."""
import sys
__path__ = []

from app.crawl import audit
from app.crawl.audit import consistency_engine, diagnostic_inventory, inventory_helper, manifest, regression_engine, ledger, snapshots, page_analysis

sys.modules["app.audit"] = sys.modules[__name__]
sys.modules["app.audit.consistency_engine"] = consistency_engine
sys.modules["app.audit.diagnostic_inventory"] = diagnostic_inventory
sys.modules["app.audit.inventory_helper"] = inventory_helper
sys.modules["app.audit.manifest"] = manifest
sys.modules["app.audit.regression_engine"] = regression_engine
sys.modules["app.audit.regression"] = regression_engine
sys.modules["app.audit.ledger"] = ledger
sys.modules["app.audit.snapshots"] = snapshots
sys.modules["app.audit.page_analysis"] = page_analysis
