# services/paystack.py
import httpx
import hashlib
import hmac
import json
from dataclasses import dataclass
from core.config import settings

PAYSTACK_BASE = 'https://api.paystack.co'

@dataclass
class PaystackError(Exception):
    status_code: int
    message: str

def _headers(secret_key: str | None = None) -> dict:
    key = secret_key or settings.PAYSTACK_SECRET_KEY
    return {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }

async def _post(endpoint: str, payload: dict, secret_key: str | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f'{PAYSTACK_BASE}{endpoint}', json=payload, headers=_headers(secret_key))
    data = resp.json()
    if not data.get('status'):
        raise PaystackError(status_code=resp.status_code, message=data.get('message', 'Paystack error'))
    return data['data']

async def _get(endpoint: str, secret_key: str | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f'{PAYSTACK_BASE}{endpoint}', headers=_headers(secret_key))
    data = resp.json()
    if not data.get('status'):
        raise PaystackError(status_code=resp.status_code, message=data.get('message', 'Paystack error'))
    return data['data']

# ── Transaction initialisation (first-time checkout) ────────────────
async def initialize_transaction(email: str, amount_kobo: int, reference: str,
                                  callback_url: str, metadata: dict = {}) -> dict:
    return await _post('/transaction/initialize', {
        'email':        email,
        'amount':       amount_kobo,
        'reference':    reference,
        'callback_url': callback_url,
        'metadata':     metadata,
    })

# ── Charge authorization (1-tap, returning user) ─────────────────────
async def charge_authorization(
    email: str,
    amount_kobo: int,
    authorization_code: str,
    reference: str,
    vendor_secret_key: str,      # MUST use the issuing vendor's secret key
) -> dict:
    return await _post('/transaction/charge_authorization', {
        'email':              email,
        'amount':             amount_kobo,
        'authorization_code': authorization_code,
        'reference':          reference,
    }, secret_key=vendor_secret_key)

# ── Transfer (disbursement to vendor) ───────────────────────────────
async def initiate_transfer(amount_kobo: int, recipient_code: str, reference: str, reason: str) -> dict:
    return await _post('/transfer', {
        'source':    'balance',
        'amount':    amount_kobo,
        'recipient': recipient_code,
        'reference': reference,
        'reason':    reason,
    })

# ── Create a transfer recipient (called once during vendor onboarding) ─
async def create_recipient(name: str, account_number: str, bank_code: str) -> dict:
    return await _post('/transferrecipient', {
        'type':           'nuban',
        'name':           name,
        'account_number': account_number,
        'bank_code':      bank_code,
        'currency':       'NGN',
    })

# ── Refund ───────────────────────────────────────────────────────────
async def refund_transaction(transaction_id: str, amount_kobo: int | None = None) -> dict:
    payload: dict = {'transaction': transaction_id}
    if amount_kobo:
        payload['amount'] = amount_kobo
    return await _post('/refund', payload)

# ── Webhook signature verification ──────────────────────────────────
def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    expected = hmac.new(
        settings.PAYSTACK_WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)

# ── Calculate Paystack's fee (for net profit ledger) ────────────────
def calculate_paystack_fee(amount_kobo: int) -> int:
    """
    Paystack fee: 1.5% + ₦100 (capped at ₦2000).
    All figures in Kobo. Returns Paystack's cut.
    """
    fee = int(amount_kobo * 0.015) + 10000   # 10000 kobo = ₦100
    return min(fee, 200000)                   # 200000 kobo = ₦2000 cap