# routers/escrow.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import get_current_user
from models.transaction import Transaction, TxStatus
from models.user import User
from tasks.escrow_release import schedule_escrow_release
from services.whatsapp import send_escrow_update
from pydantic import BaseModel
from core.config import settings

router = APIRouter(prefix='/escrow', tags=['escrow'])

class DeliveryConfirmRequest(BaseModel):
    transaction_id: str

@router.post('/confirm-delivery')
async def confirm_delivery(
    req:    DeliveryConfirmRequest,
    vendor: User = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaction).where(Transaction.id == req.transaction_id))
    txn    = result.scalar_one_or_none()

    if not txn or str(txn.vendor_id) != str(vendor.id):
        raise HTTPException(status_code=404, detail='Transaction not found')
    if txn.status != TxStatus.PAID_50:
        raise HTTPException(status_code=400, detail=f'Cannot confirm delivery in state: {txn.status}')

    txn.status       = TxStatus.DELIVERED
    txn.delivered_at = datetime.now(timezone.utc)
    await db.commit()

    # Schedule the 12-hour Celery countdown task
    schedule_escrow_release.apply_async(
        args=[str(txn.id)],
        countdown=settings.ESCROW_HOLD_HOURS * 3600,  # seconds
    )

    await send_escrow_update(
        to=vendor.phone_number,
        status='countdown',
        amount_naira=txn.second_disbursement // 100,
    )

    return {'status': 'countdown_started', 'releases_in_hours': settings.ESCROW_HOLD_HOURS}