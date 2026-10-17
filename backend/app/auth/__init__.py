import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import User, RevokedToken

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(p: str) -> str:
    return pwd.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)

def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "exp": exp,
        "jti": jti,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def revoke_token(token: str, db: Session, user_id: str | None = None) -> bool:
    """
    Revokes an active JWT token and registers its JTI in RevokedToken.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        jti = payload.get("jti") or token[:64]
        exp_ts = payload.get("exp")
        exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc).replace(tzinfo=None) if exp_ts else datetime.utcnow() + timedelta(hours=24)
        uid = payload.get("sub") or user_id
    except JWTError:
        jti = token[:64]
        exp_dt = datetime.utcnow() + timedelta(hours=24)
        uid = user_id

    existing = db.query(RevokedToken).filter_by(token_jti=jti).first()
    if not existing:
        db.add(RevokedToken(token_jti=jti, user_id=uid, expires_at=exp_dt))
        db.commit()
    return True

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    cred = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        uid = payload.get("sub")
        jti = payload.get("jti")
    except JWTError:
        raise cred

    if not uid:
        raise cred

    # Check session revocation (by JTI or token prefix)
    if jti and db.query(RevokedToken).filter_by(token_jti=jti).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if db.query(RevokedToken).filter_by(token_jti=token[:64]).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_roles(*roles: str):
    """
    Enforces that the authenticated user possesses one of the authorized roles.
    Raises 403 Forbidden with detailed role requirement message otherwise.
    """
    def role_dependency(user: User = Depends(current_user)) -> User:
        user_role = (user.role or "VIEWER").upper()
        allowed = {r.upper() for r in roles}
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for role {user_role}. Required role: {', '.join(sorted(allowed))}",
            )
        return user
    return role_dependency
