import os
from pathlib import Path
import re
import uuid

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

_CAPTURE_ID = re.compile(r"[A-Za-z0-9_-]{5,64}")


def valid_capture_id(value: str) -> bool:
    return bool(_CAPTURE_ID.fullmatch(value or ""))


async def create_order(amount: str, currency: str = "USD") -> dict:
    """Create a sandbox order; a test buyer must approve it via the returned link."""
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": currency, "value": amount}}],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "user_action": "PAY_NOW",
                        "return_url": "https://example.com/return",
                        "cancel_url": "https://example.com/cancel",
                    }
                }
            },
        }
        r = await client.post(
            f"{BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "PayPal-Request-Id": str(uuid.uuid4())},
            json=body,
        )
        if r.is_error:
            raise RuntimeError(f"PayPal create order error: {r.status_code} {r.text}")
        data = r.json()
        link = next(
            (l["href"] for l in data.get("links", []) if l.get("rel") in ("payer-action", "approve")),
            None,
        )
        return {"order_id": data["id"], "approve_url": link}


async def capture_order(order_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        r = await client.post(
            f"{BASE}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        if r.is_error:
            raise RuntimeError(f"PayPal capture error: {r.status_code} {r.text}")
        cap = r.json()["purchase_units"][0]["payments"]["captures"][0]
        return {"capture_id": cap["id"], "status": cap["status"], "amount": cap["amount"]}


async def refund_capture(
    capture_id: str, amount: str, currency: str = "USD",
    note: str = "", request_id: str | None = None,
) -> dict:
    if not valid_capture_id(capture_id):
        raise RuntimeError("Invalid capture id")
    body = {"amount": {"value": amount, "currency_code": currency}}
    if note:
        body["note_to_payer"] = note[:255]
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        r = await client.post(
            f"{BASE}/v2/payments/captures/{capture_id}/refund",
            headers={
                "Authorization": f"Bearer {token}",
                "PayPal-Request-Id": request_id or str(uuid.uuid4()),
            },
            json=body,
        )
        if r.is_error:
            raise RuntimeError(f"PayPal refund error: {r.status_code} {r.text}")
        return r.json()