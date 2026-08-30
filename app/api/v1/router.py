from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    companies,
    documents,
    drivers_packs,
    invoices,
    sync,
    templates,
    tenant,
    trips,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(tenant.router, prefix="/tenant", tags=["tenant"])
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(admin.router, prefix="/platform", tags=["platform-admin"])
router.include_router(trips.router, prefix="/trips", tags=["trips"])
router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
router.include_router(drivers_packs.router, prefix="/drivers-packs", tags=["drivers-packs"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(sync.router, prefix="/sync", tags=["sync"])
router.include_router(templates.router, prefix="/admin", tags=["admin-templates"])
