from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_current_user, get_db
from app.models.company import Company
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[CompanyResponse])
async def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Company).where(Company.tenant_id == tenant.id)
    count_stmt = select(func.count()).select_from(Company).where(Company.tenant_id == tenant.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        condition = or_(Company.legal_name.ilike(term), Company.email.ilike(term), Company.phone.ilike(term), Company.vat_number.ilike(term))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(Company.legal_name.asc()).offset((page - 1) * per_page).limit(per_page)
    )
    companies = result.scalars().all()
    return PaginatedResponse(
        items=[CompanyResponse.model_validate(company) for company in companies],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = Company(tenant_id=tenant.id, **body.model_dump())
    db.add(company)
    await db.flush()
    await db.refresh(company)
    await db.commit()
    return CompanyResponse.model_validate(company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    body: CompanyUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await db.scalar(select(Company).where(Company.id == company_id, Company.tenant_id == tenant.id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    company.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(company)
    await db.commit()
    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await db.scalar(select(Company).where(Company.id == company_id, Company.tenant_id == tenant.id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    await db.delete(company)
    await db.flush()
    await db.commit()
    return {"message": "Company deleted", "id": str(company_id)}
