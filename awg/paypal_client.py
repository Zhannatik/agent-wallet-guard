import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# .env лежит в корне проекта, на уровень выше папки awg
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE = "https://api-m.sandbox.paypal.com"


def _credentials() -> tuple[str, str]:
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    secret = os.getenv("PAYPAL_SECRET")
    if not client_id or not secret:
        raise RuntimeError(
            "PAYPAL_CLIENT_ID / PAYPAL_SECRET not set. Check the .env file in the project root."
        )
    return client_id, secret


async def _get_token(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{BASE}/v1/oauth2/token",
        auth=_credentials(),
        data={"grant_type": "client_credentials"},
    )
    if r.is_error:
        raise RuntimeError(f"PayPal auth failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


async def create_invoice_draft(
    email: str, description: str, amount: str, currency: str = "USD"
) -> dict:
    """Create a draft invoice in the PayPal sandbox."""
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        body = {
            "detail": {"currency_code": currency},
            "primary_recipients": [{"billing_info": {"email_address": email}}],
            "items": [
                {
                    "name": description,
                    "quantity": "1",
                    "unit_amount": {"currency_code": currency, "value": amount},
                }
            ],
        }
        r = await client.post(
            f"{BASE}/v2/invoicing/invoices",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        if r.is_error:
            raise RuntimeError(f"PayPal invoice error: {r.status_code} {r.text}")
        return r.json()