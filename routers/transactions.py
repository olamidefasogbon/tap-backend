# routers/transactions.py
import uuid, secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import get_current_user
from models.user import User, UserRole
from models.transaction import Transaction, TxStatus
from models.ledger import PlatformLedger
from services.escrow import calculate_escrow_split
from services.whatsapp import send_payment_link
from core.config import settings
from pydantic import BaseModel

router = APIRouter(prefix='/transactions', tags=['transactions'])

class CreateLinkRequest(BaseModel):
    product_name:    str
    amount_naira:    int          # Frontend sends Naira; we convert to Kobo internally
    buyer_phone:     str          # WhatsApp number to send the link to
    expires_hours:   int = 24

class CreateLinkResponse(BaseModel):
    transaction_id:  str
    payment_url:     str
    amount_naira:    int
    tap_fee_naira:   int
    vendor_net_naira:int

@router.post('/create-link', response_model=CreateLinkResponse)
async def create_payment_link(
    req:     CreateLinkRequest,
    vendor:  User    = Depends(get_current_user),
    db:      AsyncSession = Depends(get_db),
):
    if vendor.role != UserRole.VENDOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Vendor access required')

    amount_kobo = req.amount_naira * 100
    split       = calculate_escrow_split(amount_kobo)
    slug        = secrets.token_urlsafe(8)   # e.g. 'aB3xK9mQ'
    reference   = f'tap_{uuid.uuid4().hex[:16]}'

    txn = Transaction(
        vendor_id=vendor.id,
        product_name=req.product_name,
        amount=amount_kobo,
        tap_fee=split['tap_fee'],
        vendor_net=split['vendor_net'],
        first_disbursement=split['first_disbursement'],
        second_disbursement=split['second_disbursement'],
        status=TxStatus.PENDING,
        paystack_reference=reference,
        link_slug=slug,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=req.expires_hours),
    )
    db.add(txn)
    await db.flush()   # Get txn.id before commit

    payment_url = f'{settings.BASE_URL}/pay/{slug}'
    # Fire-and-forget WhatsApp notification
    await send_payment_link(
        phone_number=req.buyer_phone,
        product_name=req.product_name,
        amount=req.amount_naira,
        link=payment_url,
    )

    return CreateLinkResponse(
        transaction_id=str(txn.id),
        payment_url=payment_url,
        amount_naira=req.amount_naira,
        tap_fee_naira=split['tap_fee'] // 100,
        vendor_net_naira=split['vendor_net'] // 100,
    )