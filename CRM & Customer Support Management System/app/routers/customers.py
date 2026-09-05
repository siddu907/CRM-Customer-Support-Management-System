from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import CurrentUser, DbSession, require_roles
from app.core.enums import UserRole
from app.models.customer import Customer
from app.repositories.customer import CustomerRepository
from app.schemas.common import Page
from app.schemas.customers import CustomerCreate, CustomerOut, CustomerUpdate
from app.schemas.tickets import TicketOut
from app.services.customer import CustomerService
from app.services.ticket import TicketService
from app.utils.helpers import page_response

router = APIRouter()


def customer_access(customer: Customer, actor) -> None:
    if actor.role == UserRole.ADMIN.value or actor.role == UserRole.SUPPORT_AGENT.value:
        return
    if customer.user_id != actor.id:
        raise HTTPException(status_code=403, detail="You can access only your customer profile")


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT))):
    return CustomerService(db).create(current_user, data)


@router.get("", response_model=Page)
def list_customers(db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT)), search: str | None = None, status_filter: str | None = Query(default=None, alias="status"), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    items, total = CustomerRepository(db).filtered(search=search, status=status_filter, page=page, limit=limit)
    return page_response([CustomerOut.model_validate(item).model_dump() for item in items], total, page, limit)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, current_user: CurrentUser, db: DbSession):
    customer = CustomerRepository(db).get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer_access(customer, current_user)
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerUpdate, current_user: CurrentUser, db: DbSession):
    customer = CustomerRepository(db).get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer_access(customer, current_user)
    if current_user.role == UserRole.CUSTOMER.value and "status" in data.model_fields_set:
        raise HTTPException(status_code=403, detail="Customers cannot change account status")
    return CustomerService(db).update(current_user, customer, data)


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN))):
    customer = CustomerRepository(db).get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    CustomerService(db).delete(current_user, customer)
    return {"message": "Customer deleted successfully"}


@router.get("/{customer_id}/tickets", response_model=Page)
def customer_tickets(customer_id: int, current_user: CurrentUser, db: DbSession, status_filter: str | None = Query(default=None, alias="status"), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    customer = CustomerRepository(db).get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer_access(customer, current_user)
    items, total = TicketService(db).tickets.filtered(customer_id=customer.id, status=status_filter, page=page, limit=limit)
    return page_response([TicketOut.model_validate(item).model_dump() for item in items], total, page, limit)
