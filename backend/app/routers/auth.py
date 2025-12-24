"""
Credit Engine 2.0 - Authentication Router
Handles user registration, login, session verification, and profile management.
"""
from uuid import uuid4
from datetime import datetime
from typing import Optional, List
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import UserDB
from ..auth import hash_password, verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


# -----------------------------------------------------------------------------
# PROFILE MODELS
# -----------------------------------------------------------------------------

class PreviousAddress(BaseModel):
    """Previous address entry."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    # Identity Information
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None  # Jr, Sr, II, III, IV
    date_of_birth: Optional[str] = None  # ISO format: YYYY-MM-DD
    ssn_last_4: Optional[str] = None
    phone: Optional[str] = None

    # Current Address
    street_address: Optional[str] = None
    unit: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None  # 2-letter state code
    zip_code: Optional[str] = None
    move_in_date: Optional[str] = None  # ISO format: YYYY-MM-DD

    # Previous Addresses
    previous_addresses: Optional[List[PreviousAddress]] = None

    # Credit Goal (for Copilot Engine)
    credit_goal: Optional[str] = None  # mortgage, auto_loan, prime_credit_card, apartment_rental, employment, credit_hygiene

    @field_validator('credit_goal')
    @classmethod
    def validate_credit_goal(cls, v):
        if v is not None:
            valid_goals = ['mortgage', 'auto_loan', 'prime_credit_card', 'apartment_rental', 'employment', 'credit_hygiene']
            if v.lower() not in valid_goals:
                raise ValueError(f'Invalid credit goal. Must be one of: {", ".join(valid_goals)}')
            return v.lower()
        return v

    @field_validator('suffix')
    @classmethod
    def validate_suffix(cls, v):
        if v is not None:
            valid_suffixes = ['Jr', 'Sr', 'II', 'III', 'IV', 'V', 'Jr.', 'Sr.']
            if v not in valid_suffixes:
                raise ValueError(f'Invalid suffix. Must be one of: {", ".join(valid_suffixes)}')
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        if v is not None:
            valid_states = [
                'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
                'DC', 'PR', 'VI', 'GU', 'AS', 'MP'  # Territories
            ]
            if v.upper() not in valid_states:
                raise ValueError('Invalid state code')
            return v.upper()
        return v

    @field_validator('ssn_last_4')
    @classmethod
    def validate_ssn(cls, v):
        if v is not None:
            if not re.match(r'^\d{4}$', v):
                raise ValueError('SSN last 4 must be exactly 4 digits')
        return v

    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v):
        if v is not None:
            if not re.match(r'^\d{5}(-\d{4})?$', v):
                raise ValueError('Invalid ZIP code format (use 12345 or 12345-6789)')
        return v


class ChangePasswordRequest(BaseModel):
    """Request model for changing password."""
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


class UserProfileResponse(BaseModel):
    """Full user profile response."""
    id: str
    email: str
    username: str
    created_at: Optional[str] = None

    # Identity
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None
    date_of_birth: Optional[str] = None
    ssn_last_4: Optional[str] = None
    phone: Optional[str] = None

    # Current Address
    street_address: Optional[str] = None
    unit: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    move_in_date: Optional[str] = None

    # Previous Addresses
    previous_addresses: Optional[List[PreviousAddress]] = None

    # Profile completeness
    profile_complete: int = 0

    # Credit Goal (for Copilot Engine)
    credit_goal: Optional[str] = None


class UserResponse(BaseModel):
    """Basic user response (for backwards compatibility)."""
    id: str
    email: str
    username: str
    credit_goal: Optional[str] = None  # For Copilot integration
    role: str = "user"  # For Admin System


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    """
    # Check if email already exists
    existing_email = db.query(UserDB).filter(UserDB.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    existing_username = db.query(UserDB).filter(UserDB.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create new user
    user = UserDB(
        id=str(uuid4()),
        email=request.email,
        username=request.username,
        password_hash=hash_password(request.password)
    )

    db.add(user)
    db.commit()

    logger.info(f"User registered: {request.email}")
    return MessageResponse(message="User created successfully")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    # Find user by email
    user = db.query(UserDB).filter(UserDB.email == request.email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with role
    access_token = create_access_token(user.id, user.email, user.role or "user")

    logger.info(f"User logged in: {request.email}")
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserDB = Depends(get_current_user)):
    """
    Get current authenticated user info (basic).
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        credit_goal=current_user.credit_goal or "credit_hygiene",
        role=current_user.role or "user"
    )


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================

def _calculate_profile_completeness(user: UserDB) -> int:
    """Calculate profile completeness percentage based on filled fields."""
    fields = [
        user.first_name,
        user.last_name,
        user.date_of_birth,
        user.phone,
        user.street_address,
        user.city,
        user.state,
        user.zip_code,
    ]
    filled = sum(1 for f in fields if f is not None and str(f).strip())
    return int((filled / len(fields)) * 100)


def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: UserDB = Depends(get_current_user)):
    """
    Get full user profile including identity and location information.
    This data fuels the audit engine (SOL calculations, Mixed File detection).
    """
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,

        # Identity
        first_name=current_user.first_name,
        middle_name=current_user.middle_name,
        last_name=current_user.last_name,
        suffix=current_user.suffix,
        date_of_birth=_format_datetime(current_user.date_of_birth),
        ssn_last_4=current_user.ssn_last_4,
        phone=current_user.phone,

        # Current Address
        street_address=current_user.street_address,
        unit=current_user.unit,
        city=current_user.city,
        state=current_user.state,
        zip_code=current_user.zip_code,
        move_in_date=_format_datetime(current_user.move_in_date),

        # Previous Addresses
        previous_addresses=[
            PreviousAddress(**addr) for addr in (current_user.previous_addresses or [])
        ],

        # Profile completeness
        profile_complete=_calculate_profile_completeness(current_user),

        # Credit Goal
        credit_goal=current_user.credit_goal or "credit_hygiene"
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile information.
    All fields are optional - only provided fields will be updated.
    """
    # Debug logging
    logger.info(f"Profile update request received for user: {current_user.email}")
    logger.info(f"Request data: first_name={request.first_name}, last_name={request.last_name}, suffix={request.suffix}, state={request.state}")

    # Update identity fields
    if request.first_name is not None:
        current_user.first_name = request.first_name
    if request.middle_name is not None:
        current_user.middle_name = request.middle_name
    if request.last_name is not None:
        current_user.last_name = request.last_name
    if request.suffix is not None:
        current_user.suffix = request.suffix
    if request.date_of_birth is not None:
        try:
            current_user.date_of_birth = datetime.strptime(request.date_of_birth, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    if request.ssn_last_4 is not None:
        current_user.ssn_last_4 = request.ssn_last_4
    if request.phone is not None:
        current_user.phone = request.phone

    # Update address fields
    if request.street_address is not None:
        current_user.street_address = request.street_address
    if request.unit is not None:
        current_user.unit = request.unit
    if request.city is not None:
        current_user.city = request.city
    if request.state is not None:
        current_user.state = request.state
    if request.zip_code is not None:
        current_user.zip_code = request.zip_code
    if request.move_in_date is not None:
        try:
            current_user.move_in_date = datetime.strptime(request.move_in_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid move_in_date format. Use YYYY-MM-DD"
            )

    # Update previous addresses
    if request.previous_addresses is not None:
        current_user.previous_addresses = [addr.model_dump() for addr in request.previous_addresses]

    # Update credit goal
    if request.credit_goal is not None:
        current_user.credit_goal = request.credit_goal

    # Update profile completeness
    current_user.profile_complete = _calculate_profile_completeness(current_user)

    # Save to database
    db.commit()
    db.refresh(current_user)

    logger.info(f"Profile updated for user: {current_user.email}")

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,

        # Identity
        first_name=current_user.first_name,
        middle_name=current_user.middle_name,
        last_name=current_user.last_name,
        suffix=current_user.suffix,
        date_of_birth=_format_datetime(current_user.date_of_birth),
        ssn_last_4=current_user.ssn_last_4,
        phone=current_user.phone,

        # Current Address
        street_address=current_user.street_address,
        unit=current_user.unit,
        city=current_user.city,
        state=current_user.state,
        zip_code=current_user.zip_code,
        move_in_date=_format_datetime(current_user.move_in_date),

        # Previous Addresses
        previous_addresses=[
            PreviousAddress(**addr) for addr in (current_user.previous_addresses or [])
        ],

        # Profile completeness
        profile_complete=current_user.profile_complete or 0,

        # Credit Goal
        credit_goal=current_user.credit_goal or "credit_hygiene"
    )


@router.put("/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    Requires current password for verification.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.password_hash = hash_password(request.new_password)
    db.commit()

    logger.info(f"Password changed for user: {current_user.email}")
    return MessageResponse(message="Password updated successfully")
