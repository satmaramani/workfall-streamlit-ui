from __future__ import annotations

import os

CONCIERGE_BASE_URL = os.getenv("CONCIERGE_BASE_URL", "http://localhost:8000")
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8001")
INVOICE_BASE_URL = os.getenv("INVOICE_BASE_URL", "http://localhost:8002")
MARKET_INTELLIGENCE_BASE_URL = os.getenv("MARKET_INTELLIGENCE_BASE_URL", "http://localhost:8003")
TRULENS_PORT = os.getenv("TRULENS_PORT", "8502")
