from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.models import User
from app.schemas import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.security import create_access_token, hash_password, verify_password


def register_user(db: Session, data: UserRegisterRequest) -> User:
    """
    Register a new user with a hashed password.
    Returns 409 Conflict if email is already taken.
    """
    normalized_email = data.email.strip().lower()

    # Check for existing user
    stmt = select(User).where(User.email == normalized_email)
    existing_user = db.execute(stmt).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists",
        )

    hashed_pw = hash_password(data.password)
    user = User(
        email=normalized_email,
        display_name=data.display_name,
        password_hash=hashed_pw,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists",
        )


def authenticate_user(db: Session, data: UserLoginRequest) -> TokenResponse:
    """
    Verify user credentials and return signed access token.
    Returns generic 401 error that never discloses whether the email exists.
    """
    normalized_email = data.email.strip().lower()

    stmt = select(User).where(User.email == normalized_email)
    user = db.execute(stmt).scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = create_access_token(subject=str(user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )
