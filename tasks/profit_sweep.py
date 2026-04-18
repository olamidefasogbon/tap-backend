# tasks/profit_sweep.py
import asyncio
import uuid
from celery import shared_task
from sqlalchemy import select
from datetime import datetime, timezone
from core.database import AsyncSessionLocal
from models.ledger import PlatformLedger, SweepStatus
from services import paystack as ps
from core.config import settings

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def nightly_profit_sweep(self):
    asyncio.get_event_loop().run_until_complete(_sweep(self))

async def _sweep(task):
    async with AsyncSessionLocal() as db:
        # Fetch all un-swept profit rows
        result = await db.execute(
            select(PlatformLedger)
            .where(PlatformLedger.sweep_status == SweepStatus.PENDING)
            .where(PlatformLedger.tap_net_profit > 0)
        )
        rows = result.scalars().all()

        if not rows:
            return  # Nothing to sweep tonight

        total_profit = sum(r.tap_net_profit for r in rows)
        sweep_ref    = f'tap_sweep_{uuid.uuid4().hex[:12]}'

        try:
            await ps.initiate_transfer(
                amount_kobo=total_profit,
                recipient_code=settings.PAYSTACK_CORPORATE_ACCOUNT_CODE,
                reference=sweep_ref,
                reason=f'tap. nightly profit sweep — {len(rows)} transactions',
            )
        except Exception as exc:
            raise task.retry(exc=exc)

        # Mark all rows as swept
        now = datetime.now(timezone.utc)
        for row in rows:
            row.sweep_status       = SweepStatus.SWEPT
            row.swept_at           = now
            row.sweep_transfer_ref = sweep_ref
            
        await db.commit()