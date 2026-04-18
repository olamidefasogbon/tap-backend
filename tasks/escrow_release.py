# tasks/escrow_release.py
import asyncio
from celery import shared_task
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.transaction import Transaction, TxStatus
from models.user import User
from services import paystack as ps
from services.whatsapp import send_escrow_update

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def schedule_escrow_release(self, transaction_id: str):
    """
    Celery task called 12 hours after delivery confirmation.
    Releases the second 50% disbursement unless status is DISPUTED.
    """
    # Run the async function inside the sync Celery worker
    asyncio.get_event_loop().run_until_complete(_release(self, transaction_id))

async def _release(task, transaction_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        txn    = result.scalar_one_or_none()

        if not txn:
            return  # Should not happen; log and exit

        if txn.status == TxStatus.DISPUTED:
            # Funds frozen — admin must manually resolve
            return

        if txn.status != TxStatus.DELIVERED:
            # Already settled or refunded by another path
            return

        # Fetch vendor
        vendor_result = await db.execute(select(User).where(User.id == txn.vendor_id))
        vendor        = vendor_result.scalar_one()

        try:
            transfer_ref_2 = f'tap_d2_{txn.id.hex[:12]}'
            await ps.initiate_transfer(
                amount_kobo=txn.second_disbursement,
                recipient_code=vendor.paystack_recipient_code,
                reference=transfer_ref_2,
                reason=f'tap. final disbursement — {txn.product_name}',
            )
            
            txn.status                  = TxStatus.SETTLED
            txn.paystack_transfer_ref_2 = transfer_ref_2
            
            from datetime import datetime, timezone
            txn.settled_at              = datetime.now(timezone.utc)
            await db.commit()

            await send_escrow_update(
                to=vendor.phone_number,
                status='settled',
                amount_naira=txn.second_disbursement // 100,
            )
        except Exception as exc:
            await db.rollback()
            raise task.retry(exc=exc)