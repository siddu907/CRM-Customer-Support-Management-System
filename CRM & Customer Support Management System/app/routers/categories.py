from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import CurrentUser, DbSession, require_roles
from app.core.enums import UserRole
from app.repositories.category import CategoryRepository
from app.schemas.categories import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.category import CategoryService

router = APIRouter()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN))):
    return CategoryService(db).create(current_user, data)


@router.get("", response_model=list[CategoryOut])
def list_categories(current_user: CurrentUser, db: DbSession, search: str | None = None, active_only: bool | None = Query(None, description="true returns active categories; false returns inactive categories; omit to return both")):
    return CategoryRepository(db).filtered(search, active_only)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, current_user: CurrentUser, db: DbSession):
    category = CategoryRepository(db).get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN))):
    category = CategoryRepository(db).get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryService(db).update(current_user, category, data)


@router.delete("/{category_id}")
def delete_category(category_id: int, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN))):
    category = CategoryRepository(db).get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    CategoryService(db).delete(current_user, category)
    return {"message": "Category deleted successfully"}
