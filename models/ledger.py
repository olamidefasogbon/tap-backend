# models/ledger.py — Platform profit tracker (anti-commingling)
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class SweepStatus(PyEnum):
    PENDING = 'pending'  # Profit accrued, not yet swept
    SWEPT   = 'swept'    # Transferred to corporate account

class PlatformLedger(Base):
    __tablename__ = 'platform_ledger'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('transactions.id'), unique=True, nullable=False)
    
    total_volume: Mapped[int] = mapped_column(Integer, nullable=False)   # Buyer paid (Kobo)
    paystack_fee: Mapped[int] = mapped_column(Integer, nullable=False)   # Paystack's cut
    tap_gross_profit: Mapped[int] = mapped_column(Integer, nullable=False)   # tap_fee charged
    tap_net_profit: Mapped[int] = mapped_column(Integer, nullable=False)   # tap_fee - paystack_fee
    
    sweep_status: Mapped[SweepStatus] = mapped_column(Enum(SweepStatus), default=SweepStatus.PENDING)
    swept_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    sweep_transfer_ref: Mapped[str|None] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())