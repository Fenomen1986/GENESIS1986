# bots_factory/app/web/security.py

from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models, crud
from .database import get_db

SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

SUPERADMIN_USERNAME = "superadmin"
SUPERADMIN_PASSWORD = "superadmin_password_change_me"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("superadmin"):
             raise credentials_exception
        username: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if username is None or tenant_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_username(db, username=username)
    if user is None or user.tenant_id != tenant_id:
        raise credentials_exception
    return user

async def get_current_superadmin_user(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authorized as superadmin",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("superadmin"):
            raise credentials_exception
        return payload.get("sub")
    except (JWTError, AttributeError):
        raise credentials_exception

def is_superadmin(username, password):
    return username == SUPERADMIN_USERNAME and password == SUPERADMIN_PASSWORD

def is_superadmin_user_created(db: Session):
    return db.query(models.User).filter(models.User.username == SUPERADMIN_USERNAME).first() is not None

def create_superadmin_user(db: Session):
    if not is_superadmin_user_created(db):
        sa_user = models.User(
            username=SUPERADMIN_USERNAME,
            hashed_password=get_password_hash(SUPERADMIN_PASSWORD),
            tenant_id=None
        )
        db.add(sa_user)
        db.commit()