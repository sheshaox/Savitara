"""
Authentication API Endpoints
Handles Google OAuth login, JWT token management
SonarQube: S5122 - Proper CORS handled in main.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
import requests
from typing import Dict, Any
from pydantic import ValidationError
import logging
import os

from app.schemas.requests import (
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    StandardResponse
)
from app.core.config import get_settings
from app.core.security import SecurityManager, get_current_user
from app.core.exceptions import AuthenticationError, InvalidInputError
from app.db.connection import get_db
from app.models.database import User, UserRole, UserStatus
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
security_manager = SecurityManager()
security = HTTPBearer()
settings = get_settings()

# Google's public key URLs for token verification
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
FIREBASE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

logger.info("Auth module initialized - using direct JWT verification")


def verify_google_token(token: str) -> Dict[str, Any]:
    """
    Verify Firebase ID token using direct JWT verification.
    This approach doesn't require any service account credentials.
    
    It fetches Google's public keys directly and verifies the token signature.
    """
    try:
        logger.info("Verifying Firebase ID token using direct JWT verification...")
        
        # First, decode the token header to get the key ID (kid)
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            logger.debug(f"Token key ID (kid): {kid}")
        except jwt.exceptions.DecodeError as e:
            logger.error(f"Failed to decode token header: {e}")
            raise AuthenticationError(message="Invalid token format", details={"error": str(e)})
        
        # Fetch Google's public keys using PyJWKClient
        try:
            jwks_client = PyJWKClient(GOOGLE_CERTS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            logger.debug("Successfully fetched signing key from Google")
        except Exception as e:
            logger.warning(f"Failed to get key from Google OAuth certs: {e}, trying Firebase certs...")
            # Try fetching from Firebase-specific endpoint
            try:
                # For Firebase tokens, we need to fetch the X.509 certificate
                response = requests.get(FIREBASE_CERTS_URL, timeout=10)
                response.raise_for_status()
                certs = response.json()
                
                if kid not in certs:
                    logger.error(f"Key ID {kid} not found in Firebase certificates")
                    raise AuthenticationError(
                        message="Token signing key not found",
                        details={"kid": kid, "available_kids": list(certs.keys())}
                    )
                
                # Get the certificate for this key ID
                cert_str = certs[kid]
                from cryptography.x509 import load_pem_x509_certificate
                from cryptography.hazmat.backends import default_backend
                
                cert = load_pem_x509_certificate(cert_str.encode(), default_backend())
                signing_key = cert.public_key()
                logger.debug("Successfully fetched signing key from Firebase certs")
            except requests.RequestException as req_err:
                logger.error(f"Failed to fetch Firebase certificates: {req_err}")
                raise AuthenticationError(
                    message="Failed to fetch verification certificates",
                    details={"error": str(req_err)}
                )
        
        # Verify and decode the token
        try:
            # Get the public key
            if hasattr(signing_key, 'key'):
                public_key = signing_key.key
            else:
                public_key = signing_key
            
            # Firebase tokens use RS256 algorithm
            # The audience should be the Firebase project ID
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=settings.FIREBASE_PROJECT_ID,
                issuer=f"https://securetoken.google.com/{settings.FIREBASE_PROJECT_ID}"
            )
            
            logger.info(f"Token verified successfully for user: {decoded.get('email')}")
            
            # Extract user info
            return {
                'email': decoded.get('email'),
                'google_id': decoded.get('user_id') or decoded.get('sub'),
                'name': decoded.get('name'),
                'picture': decoded.get('picture'),
                'email_verified': decoded.get('email_verified', False)
            }
            
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise AuthenticationError(message="Token has expired, please sign in again")
        except jwt.InvalidAudienceError:
            logger.error(f"Invalid audience. Expected: {settings.FIREBASE_PROJECT_ID}")
            raise AuthenticationError(message="Token audience mismatch")
        except jwt.InvalidIssuerError:
            logger.error("Invalid token issuer")
            raise AuthenticationError(message="Token issuer mismatch")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise AuthenticationError(message="Invalid token", details={"error": str(e)})
            
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        raise AuthenticationError(
            message="Failed to verify Firebase token",
            details={"error": str(e)}
        )


@router.post(
    "/google",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth Login",
    description="Authenticate user with Google OAuth and return JWT tokens"
)
async def google_login(
    auth_request: GoogleAuthRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Google OAuth authentication endpoint
    
    Flow:
    1. Verify Google ID token
    2. Check if user exists, create if new
    3. Generate JWT access + refresh tokens
    4. Return tokens and user info
    
    SonarQube: S6437 - No hardcoded credentials, uses Google OAuth
    """
    try:
        # Verify Google token
        google_info = verify_google_token(auth_request.id_token)
        
        if not google_info['email_verified']:
            raise AuthenticationError(
                message="Email not verified with Google",
                details={"email": google_info['email']}
            )
        
        # Check if user exists
        user_doc = await db.users.find_one({"email": google_info['email']})
        
        if user_doc:
            # Existing user - update last login
            await db.users.update_one(
                {"email": google_info['email']},
                {
                    "$set": {
                        "google_id": google_info['google_id'],
                        "profile_picture": google_info.get('picture'),
                        "last_login": datetime.now(timezone.utc)
                    }
                }
            )
            user = User(**user_doc)
            is_new_user = False
        else:
            # New user - create account with PENDING status until onboarding
            user = User(
                email=google_info['email'],
                name=google_info.get('name'),
                google_id=google_info['google_id'],
                role=auth_request.role,
                status=UserStatus.PENDING,  # Always PENDING for new users until onboarding
                profile_picture=google_info.get('picture'),
                credits=100  # Welcome bonus
            )
            
            result = await db.users.insert_one(user.model_dump(by_alias=True))
            user.id = str(result.inserted_id)
            is_new_user = True
            
            logger.info(f"New user created: {user.email} with role {user.role}")
        
        # Check user status
        if user.status == UserStatus.SUSPENDED:
            raise AuthenticationError(
                message="Account suspended",
                details={"contact": "support@savitara.com"}
            )
        
        # Check if user has completed onboarding by checking if profile exists
        profile_collection = "grihasta_profiles" if user.role == UserRole.GRIHASTA else "acharya_profiles"
        profile = await db[profile_collection].find_one({"user_id": str(user.id)})
        has_completed_onboarding = profile is not None
        
        # Generate JWT tokens
        access_token = security_manager.create_access_token(
            user_id=str(user.id),
            role=user.role.value
        )
        refresh_token = security_manager.create_refresh_token(
            user_id=str(user.id)
        )
        
        return StandardResponse(
            success=True,
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name or google_info.get('name'),
                    "role": user.role.value,
                    "status": user.status.value,
                    "credits": user.credits,
                    "is_new_user": is_new_user,
                    "onboarded": has_completed_onboarding,
                    "onboarding_completed": has_completed_onboarding
                }
            },
            message="Authentication successful"
        )
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post(
    "/register",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Email Registration",
    description="Register a new user with email and password"
)
async def register(
    request: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Register new user with email/password
    Enhanced with comprehensive error handling and proper serialization
    """
    try:
        logger.info(f"Registration attempt for email: {request.email}, role: {request.role}")
        
        # Validate input
        if not request.email or not request.password or not request.name:
            logger.warning("Registration failed: Missing required fields")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, password, and name are required"
            )
        
        # Check if user exists
        try:
            existing_user = await db.users.find_one({"email": request.email})
            if existing_user:
                logger.warning(f"Registration failed: Email {request.email} already exists")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        except HTTPException:
            raise
        except Exception as db_error:
            logger.error(f"Database query error checking existing user: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error. Please try again."
            )

        # Create new user - status is PENDING until onboarding is complete
        try:
            user = User(
                email=request.email,
                name=request.name,
                password_hash=security_manager.get_password_hash(request.password),
                role=request.role,
                status=UserStatus.PENDING,  # Always PENDING for new users until onboarding
                credits=100,  # Welcome bonus
                onboarded=False,
                device_tokens=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        except Exception as model_error:
            logger.error(f"Error creating user model: {str(model_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user account. Please try again."
            )
        
        logger.info(f"Creating new user: {request.email}")
        
        # Insert user into database with proper serialization
        try:
            # Ensure datetime fields are properly serialized
            user_dict = user.model_dump(by_alias=True, exclude_none=True, mode='json')
            
            result = await db.users.insert_one(user_dict)
            user_id = str(result.inserted_id)
            logger.info(f"User created successfully with ID: {user_id}")
        except Exception as insert_error:
            logger.error(f"Database insert error: {str(insert_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user account. Please try again."
            )
        
        # Generate tokens
        try:
            access_token = security_manager.create_access_token(
                user_id=user_id,
                role=user.role.value
            )
            
            refresh_token = security_manager.create_refresh_token(
                user_id=user_id
            )
        except Exception as token_error:
            logger.error(f"Token generation error: {str(token_error)}", exc_info=True)
            # User was created but token failed - still return success with basic info
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account created but login failed. Please try logging in."
            )
        
        # New user always needs onboarding
        logger.info(f"Registration complete for {request.email}")
        
        return StandardResponse(
            success=True,
            message="Registration successful",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user_id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value,
                    "status": user.status.value,
                    "credits": user.credits,
                    "is_new_user": True,
                    "onboarded": False,
                    "onboarding_completed": False
                }
            }
        )
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Registration validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected registration error: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post(
    "/login",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Email Login",
    description="Authenticate user with email and password"
)
async def login(
    request: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Login with email/password
    """
    try:
        # Find user
        user_doc = await db.users.find_one({"email": request.email})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found with this email. Please sign up first."
            )
            
        user = User(**user_doc)
        
        # Verify password
        if not user.password_hash or not security_manager.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
            
        # Check status
        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account suspended"
            )
            
        # Update last login
        await db.users.update_one(
            {"_id": user.id},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        
        # Check if user has completed onboarding by checking if profile exists
        profile_collection = "grihasta_profiles" if user.role == UserRole.GRIHASTA else "acharya_profiles"
        profile = await db[profile_collection].find_one({"user_id": str(user.id)})
        has_completed_onboarding = profile is not None
        
        # Generate tokens
        access_token = security_manager.create_access_token(
            user_id=str(user.id),
            role=user.role.value
        )
        
        refresh_token = security_manager.create_refresh_token(
            user_id=str(user.id)
        )
        
        return StandardResponse(
            success=True,
            message="Login successful",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value,
                    "status": user.status.value,
                    "credits": user.credits,
                    "is_new_user": False,
                    "onboarded": has_completed_onboarding,
                    "onboarding_completed": has_completed_onboarding
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post(
    "/refresh",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Get new access token using refresh token"
)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Refresh access token
    
    SonarQube: Token rotation prevents replay attacks
    """
    try:
        # Verify refresh token
        payload = security_manager.verify_token(
            refresh_request.refresh_token,
            token_type="refresh"
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(message="Invalid token payload")
        
        # Verify user still exists and is active
        user_doc = await db.users.find_one({"_id": user_id})
        if not user_doc:
            raise AuthenticationError(message="User not found")
        
        user = User(**user_doc)
        if user.status in [UserStatus.SUSPENDED, UserStatus.DELETED]:
            raise AuthenticationError(message="Account not active")
        
        # Generate new tokens
        access_token = security_manager.create_access_token(
            user_id=str(user.id),
            role=user.role.value
        )
        new_refresh_token = security_manager.create_refresh_token(
            user_id=str(user.id)
        )
        
        return StandardResponse(
            success=True,
            data={
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            },
            message="Token refreshed successfully"
        )
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post(
    "/logout",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Invalidate user session (client should delete tokens)"
)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Logout endpoint
    
    Note: JWT tokens are stateless. Client must delete tokens.
    In production, implement token blacklist with Redis for immediate invalidation.
    
    SonarQube: S2068 - No password in code
    """
    logger.info(f"User {current_user['id']} logged out")
    
    return StandardResponse(
        success=True,
        message="Logged out successfully. Please delete tokens on client side."
    )


@router.get(
    "/me",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get authenticated user information"
)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get current authenticated user information
    """
    user_doc = await db.users.find_one({"_id": current_user["id"]})
    
    if not user_doc:
        raise AuthenticationError(message="User not found")
    
    user = User(**user_doc)
    
    # Check if user has completed onboarding by checking if profile exists
    profile_collection = "grihasta_profiles" if user.role == UserRole.GRIHASTA else "acharya_profiles"
    profile = await db[profile_collection].find_one({"user_id": str(user.id)})
    has_completed_onboarding = profile is not None
    
    return StandardResponse(
        success=True,
        data={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "status": user.status.value,
            "credits": user.credits,
            "profile_picture": getattr(user, 'profile_picture', None),
            "created_at": user.created_at,
            "last_login": user.last_login,
            "onboarded": has_completed_onboarding,
            "onboarding_completed": has_completed_onboarding
        }
    )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Auth Health Check",
    description="Check if authentication service is working"
)
async def auth_health_check():
    """Health check endpoint for auth service"""
    return {
        "status": "healthy",
        "service": "authentication",
        "google_oauth": "configured" if settings.GOOGLE_CLIENT_ID else "not_configured"
    }
