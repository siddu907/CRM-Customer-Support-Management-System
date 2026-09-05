from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUser, DbSession
from app.core.enums import UserRole
from app.schemas.dashboard import DashboardOut
from app.services.dashboard import dashboard_for

router = APIRouter()


def for_role(current_user, db, role: UserRole):
    if current_user.role != role.value:
        raise HTTPException(status_code=403, detail=f"This dashboard is for {role.value} users")
    return dashboard_for(db, current_user)


@router.get("/admin", response_model=DashboardOut)
def admin_dashboard(current_user: CurrentUser, db: DbSession):
    return for_role(current_user, db, UserRole.ADMIN)


@router.get("/agent", response_model=DashboardOut)
def agent_dashboard(current_user: CurrentUser, db: DbSession):
    return for_role(current_user, db, UserRole.SUPPORT_AGENT)


@router.get("/customer", response_model=DashboardOut)
def customer_dashboard(current_user: CurrentUser, db: DbSession):
    return for_role(current_user, db, UserRole.CUSTOMER)
