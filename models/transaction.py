# models/transaction.py
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class TxStatus(PyEnum):
    PENDING        = 'pending'       # Link generated, buyer hasn't paid
    PAID_50        = 'paid_50'       # Buyer paid; first 50% released to vendor
    DELIVERED      = 'delivered'     # Vendor marked delivered; 12hr clock started
    SETTLED        = 'settled'       # Final 50% released; transaction complete
    DISPUTED       = 'disputed'      # Buyer raised dispute; funds frozen
    REFUNDED       = 'refunded'      # Full or partial refund issued
    EXPIRED        = 'expired'       # Link expired before payment

class Transaction(Base):
    __tablename__ = 'transactions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    buyer_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Amount fields — all in Kobo
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tap_fee: Mapped[int] = mapped_column(Integer, nullable=False)  # 4% of amount
    vendor_net: Mapped[int] = mapped_column(Integer, nullable=False)  # amount - tap_fee
    first_disbursement: Mapped[int] = mapped_column(Integer, nullable=False)  # vendor_net * 0.5
    second_disbursement: Mapped[int] = mapped_column(Integer, nullable=False)  # vendor_net * 0.5
    
    status: Mapped[TxStatus] = mapped_column(Enum(TxStatus), default=TxStatus.PENDING, nullable=False)
    
    # Paystack references
    paystack_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    paystack_transfer_ref_1: Mapped[str|None] = mapped_column(String(100), nullable=True)
    paystack_transfer_ref_2: Mapped[str|None] = mapped_column(String(100), nullable=True)
    
    # Link metadata
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    link_slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_one_tap: Mapped[bool] = mapped_column(Boolean, default=False)  # Analytics
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor = relationship('User', foreign_keys=[vendor_id])
    buyer  = relationship('User', foreign_keys=[buyer_id])