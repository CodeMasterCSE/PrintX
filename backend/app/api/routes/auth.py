from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse, TokenRefreshRequest
from app.services.auth_service import AuthService, require_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new student user."""
    user = AuthService.register_user(db=db, user_in=user_in)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticates a user and issues access and refresh tokens."""
    return AuthService.authenticate_user(db=db, login_data=login_data)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Refreshes an expired access token using a valid refresh token."""
    return AuthService.refresh_token(db=db, refresh_token=request.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(require_current_user)):
    """Returns the authenticated user's profile."""
    return UserResponse.model_validate(user)

