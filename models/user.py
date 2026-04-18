# models/user.py
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Numeric, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class UserRole(PyEnum):
    VENDOR = 'vendor'
    BUYER  = 'buyer'
    ADMIN  = 'admin'

class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.BUYER)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bvn: Mapped[str | None] = mapped_column(String(11), nullable=True)
    
    # Financial balances — always in Kobo (integer arithmetic avoids float errors)
    wallet_balance: Mapped[int] = mapped_column(Numeric(precision=20, scale=0), default=0, nullable=False)
    escrow_balance: Mapped[int] = mapped_column(Numeric(precision=20, scale=0), default=0, nullable=False)
    
    # Paystack recipient code — required for Transfers API disbursements
    paystack_recipient_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())