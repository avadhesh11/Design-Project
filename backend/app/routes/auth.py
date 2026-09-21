from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, UTC
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import httpx

from ..database import get_db
from ..models import User
from ..schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

SECRET = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM")

PRODUCTION = os.getenv("PRODUCTION", "false").lower() in ("true", "1")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")



def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, email: str):
    expire = datetime.now(UTC) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET,
        algorithm=ALGORITHM
    )


def create_refresh_token(user_id: str):
    expire = datetime.now(UTC) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET,
        algorithm=ALGORITHM
    )



def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str
):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True if PRODUCTION==True else False, 
        samesite="none" if PRODUCTION==True else "lax" ,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True if PRODUCTION else False,
        samesite="none" if PRODUCTION else "lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS *24*60* 60
    )


@router.post("/register")
@limiter.limit("3/minute")
def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(
        User.email == body.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Please try again or use a different email."
        )

    user = User(
        email=body.email,
        password=hash_password(body.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        str(user.id),
        user.email
    )

    refresh_token = create_refresh_token(
        str(user.id)
    )

    set_auth_cookies(
        response,
        access_token,
        refresh_token
    )

    return {
        "message": "Registered successfully"
    }

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == body.email
    ).first()

    if not user or not user.password or not verify_password(
        body.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    access_token = create_access_token(
        str(user.id),
        user.email
    )

    refresh_token = create_refresh_token(
        str(user.id)
    )

    set_auth_cookies(
        response,
        access_token,
        refresh_token
    )

    return {
        "message": "Login successful"
    }


@router.post("/refresh")
@limiter.limit("10/minute")
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="No refresh token"
        )

    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_access = create_access_token(
        str(user.id),
        user.email
    )

    new_refresh = create_refresh_token(
        str(user.id)
    )

    set_auth_cookies(
        response,
        new_access,
        new_refresh
    )

    return {
        "message": "Token refreshed"
    }



@router.post("/logout")
def logout( request: Request,response: Response):
    secure = True if PRODUCTION else False
    samesite = "none" if PRODUCTION else "lax"
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="No refresh token"
        )
    response.delete_cookie(
        "access_token",
        secure=secure,
        samesite=samesite,
        httponly=True
    )
    response.delete_cookie(
        "refresh_token",
        secure=secure,
        samesite=samesite,
        httponly=True
    )

    return {
        "message": "Logged out"
    }



@router.get("/me", response_model=UserResponse)
def me(
    request: Request,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=401,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


@router.get("/github")
def github_login():
    client_id = os.getenv("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured. Please add GITHUB_CLIENT_ID to backend/.env"
        )
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&scope=user:email"
    return RedirectResponse(url=github_auth_url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    db: Session = Depends(get_db)
):
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured. Please add GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to backend/.env"
        )

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"}
        )

        if token_res.status_code != 200:
            return RedirectResponse(
                url=f"{frontend_url}/login?error=Failed+to+communicate+with+GitHub"
            )

        token_data = token_res.json()
        github_token = token_data.get("access_token")
        if not github_token:
            error_desc = token_data.get("error_description", "GitHub authentication failed")
            return RedirectResponse(
                url=f"{frontend_url}/login?error={error_desc}"
            )

        # Get user email
        emails_res = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/json",
                "User-Agent": "OrbitAI-App"
            }
        )

        user_email = None
        if emails_res.status_code == 200:
            emails_data = emails_res.json()
            for email_info in emails_data:
                if email_info.get("primary") and email_info.get("verified"):
                    user_email = email_info.get("email")
                    break
            if not user_email and emails_data:
                user_email = emails_data[0].get("email")

        # Fallback to user profile
        if not user_email:
            profile_res = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/json",
                    "User-Agent": "OrbitAI-App"
                }
            )
            if profile_res.status_code == 200:
                profile_data = profile_res.json()
                user_email = profile_data.get("email")

        if not user_email:
            return RedirectResponse(
                url=f"{frontend_url}/login?error=Could+not+retrieve+email+from+GitHub"
            )

    # Find or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            email=user_email,
            password=None
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(str(user.id), user.email)
    refresh_token = create_refresh_token(str(user.id))

    redirect_response = RedirectResponse(
        url=f"{frontend_url}/dashboard",
        status_code=302
    )
    set_auth_cookies(redirect_response, access_token, refresh_token)
    return redirect_response



