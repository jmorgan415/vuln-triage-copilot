"""Notify the internal ledger when payments settle.

Outbound HTTPS only. Egress goes straight to the internal service mesh;
no corporate proxy is configured for this service.
"""
import requests

LEDGER_URL = "https://ledger.internal.northgate.io/v1/settlements"
TIMEOUT_S = 5.0


def notify_settlement(payment_id: str, amount_cents: int) -> bool:
    """POST a settlement event to the ledger service."""
    response = requests.post(
        LEDGER_URL,
        json={"payment_id": payment_id, "amount_cents": amount_cents},
        timeout=TIMEOUT_S,
    )
    return response.status_code == 200
