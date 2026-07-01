"""Signup/login (email+password) and Google OAuth endpoints."""

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.db_models import User
from app.logging_config import get_logger
from app.rate_limit import limiter
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services.auth_service import create_access_token, get_current_user, hash_password, verify_password

logger = get_logger(__name__)
router = APIRouter()

oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, has_password=user.hashed_password is not None)


@router.post("/api/auth/signup", response_model=TokenResponse)
@limiter.limit("5/hour")
def signup(request: Request, payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(email=payload.email.lower(), hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or user.hashed_password is None or not verify_password(payload.password, user.hashed_password):
        raise invalid

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/api/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.get("/api/auth/google/login")
async def google_login(request: Request):
    if not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login is not configured")
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/api/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login is not configured")

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error("Google OAuth token exchange failed: %s", e)
        return RedirectResponse(f"{settings.frontend_url}/login?error=google_auth_failed")

    userinfo = token.get("userinfo") or {}
    google_sub = userinfo.get("sub")
    email = userinfo.get("email")
    if not google_sub or not email:
        return RedirectResponse(f"{settings.frontend_url}/login?error=google_auth_failed")

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user is None:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            user = User(email=email.lower(), google_sub=google_sub)
            db.add(user)
        else:
            user.google_sub = google_sub
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token(user.id)
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={jwt_token}")
