# routers/webhooks.py
import json
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.database import get_db
from models.user import User
from models.transaction import Transaction, TxStatus
from models.ledger import PlatformLedger, SweepStatus
from services import paystack as ps
from services.whatsapp import send_escrow_update
from tasks.escrow_release import schedule_escrow_release
from core.config import settings

router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post('/paystack')
async def paystack_webhook(
    request:          Request,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    # ── 1. Verify signature ─────────────────────────────────────────
    body      = await request.body()
    signature = request.headers.get('x-paystack-signature', '')
    if not ps.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail='Invalid webhook signature')

    event = json.loads(body)
    if event.get('event') != 'charge.success':
        return {'status': 'ignored'}   # We only act on successful charges

    data      = event['data']
    reference = data['reference']
    amount_kobo = data['amount']

    # ── 2. Fetch transaction — guard against double-delivery ────────
    result = await db.execute(select(Transaction).where(Transaction.paystack_reference == reference))
    txn    = result.scalar_one_or_none()

    if not txn:
        return {'status': 'not_found'}
    if txn.status != TxStatus.PENDING:
        return {'status': 'already_processed'}  # Idempotent — safe to ignore

    # ── 3. Fetch vendor's recipient code ────────────────────────────
    vendor_result = await db.execute(select(User).where(User.id == txn.vendor_id))
    vendor        = vendor_result.scalar_one()
    if not vendor.paystack_recipient_code:
        raise HTTPException(status_code=500, detail='Vendor has no recipient code')

    # ── 4. Release first 50% to vendor immediately ──────────────────
    transfer_ref_1 = f'tap_d1_{txn.id.hex[:12]}'
    await ps.initiate_transfer(
        amount_kobo=txn.first_disbursement,
        recipient_code=vendor.paystack_recipient_code,
        reference=transfer_ref_1,
        reason=f'tap. first disbursement — {txn.product_name}',
    )

    # ── 5. Calculate Paystack fee and log to Platform Ledger ─────────
    paystack_fee = ps.calculate_paystack_fee(amount_kobo)
    net_profit   = txn.tap_fee - paystack_fee

    ledger_entry = PlatformLedger(
        transaction_id=txn.id,
        total_volume=amount_kobo,
        paystack_fee=paystack_fee,
        tap_gross_profit=txn.tap_fee,
        tap_net_profit=max(net_profit, 0),
        sweep_status=SweepStatus.PENDING,
    )
    db.add(ledger_entry)

    # ── 6. Update transaction state ──────────────────────────────────
    txn.status             = TxStatus.PAID_50
    txn.paystack_transfer_ref_1 = transfer_ref_1

    await db.commit()

    # ── 7. Notify vendor via WhatsApp (background — non-blocking) ───
    background_tasks.add_task(
        send_escrow_update,
        to=vendor.phone_number,
        status='paid_50',
        amount_naira=txn.vendor_net // 100,
    )

    return {'status': 'processed'}