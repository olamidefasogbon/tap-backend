# routers/auth.py
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database import get_db
from models.user import User, UserRole
from core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

# This tells the app to use bcrypt for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    phone_number: str
    password: str
    bvn: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Check if the phone number is already taken
    result = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # 2. Hash the password and save the new vendor
    hashed_password = pwd_context.hash(user_in.password)
    new_user = User(
        phone_number=user_in.phone_number,
        password_hash=hashed_password,
        role=UserRole.VENDOR,
        bvn=user_in.bvn
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 3. Generate their access token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # 1. Find the user
    result = await db.execute(select(User).where(User.phone_number == form_data.username))
    user = result.scalar_one_or_none()

    # 2. Verify the password
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Hand them a fresh token
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}