from fastapi import APIRouter, Depends, status
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import ChangePasswordRequest, LoginRequest, ProfileUpdate, RegisterRequest, TokenResponse
from app.schemas.users import UserOut
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession):
    """Public registration always creates a customer account."""
    return AuthService(db).register_customer(data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession):
    token, user = AuthService(db).login(data.email, data.password)
    return {"access_token": token, "user": user}


@router.get("/profile", response_model=UserOut)
def profile(current_user: CurrentUser):
    return current_user


@router.put("/profile", response_model=UserOut)
def update_profile(data: ProfileUpdate, current_user: CurrentUser, db: DbSession):
    return AuthService(db).update_profile(current_user, data)


@router.put("/change-password", status_code=status.HTTP_200_OK)
def change_password(data: ChangePasswordRequest, current_user: CurrentUser, db: DbSession):
    AuthService(db).change_password(current_user, data.current_password, data.new_password)
    return {"message": "Password changed successfully"}
