"""
Tenant API routes — branding, settings, company details.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.document_registry import get_all_document_types
from app.deps import get_current_tenant, get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.document import DocumentService

router = APIRouter()


class CompanyBranding(BaseModel):
    """Company branding settings for documents."""
    # Company details
    name: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    registration_number: str | None = None
    tax_number: str | None = None
    
    # Branding
    logo_storage_key: str | None = None
    primary_color: str | None = None  # Hex color, e.g., "#2c5aa0"
    secondary_color: str | None = None
    
    # Global footer text
    footer_text: str | None = None
    
    # Document-specific footers (Client documents)
    quotation_footer: str | None = None
    proforma_footer: str | None = None
    booking_footer: str | None = None
    invoice_footer: str | None = None
    credit_debit_footer: str | None = None
    
    # Document-specific footers (Carrier documents)
    load_confirmation_footer: str | None = None
    carrier_invoice_footer: str | None = None
    contract_footer: str | None = None
    
    # Document-specific footers (Operational documents)
    pod_footer: str | None = None
    packing_list_footer: str | None = None
    grn_footer: str | None = None


class BrandingResponse(BaseModel):
    """Response with branding settings."""
    # Company details
    name: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    registration_number: str | None = None
    tax_number: str | None = None
    
    # Branding
    logo_storage_key: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    
    # Global footer text
    footer_text: str | None = None
    
    # Document-specific footers
    quotation_footer: str | None = None
    proforma_footer: str | None = None
    booking_footer: str | None = None
    invoice_footer: str | None = None
    credit_debit_footer: str | None = None
    load_confirmation_footer: str | None = None
    carrier_invoice_footer: str | None = None
    contract_footer: str | None = None
    pod_footer: str | None = None
    packing_list_footer: str | None = None
    grn_footer: str | None = None
    
    # Document categories summary (each category contains list of dicts with keys)
    document_categories: dict[str, list[dict[str, Any]]] | None = None

    model_config = {"from_attributes": True}


def _extract_branding_from_settings(tenant: Tenant) -> dict:
    """Extract branding data from tenant settings."""
    settings = tenant.settings or {}
    branding = settings.get("branding", {})
    
    return {
        "name": tenant.name,
        "address": settings.get("address"),
        "city": settings.get("city"),
        "postal_code": settings.get("postal_code"),
        "country": settings.get("country"),
        "phone": settings.get("phone"),
        "email": settings.get("email"),
        "website": settings.get("website"),
        "registration_number": settings.get("registration_number"),
        "tax_number": settings.get("tax_number"),
        "logo_storage_key": branding.get("logo_storage_key"),
        "primary_color": branding.get("primary_color", "#2c5aa0"),
        "secondary_color": branding.get("secondary_color"),
        "footer_text": branding.get("footer_text"),
        "quotation_footer": branding.get("quotation_footer"),
        "proforma_footer": branding.get("proforma_footer"),
        "booking_footer": branding.get("booking_footer"),
        "invoice_footer": branding.get("invoice_footer"),
        "credit_debit_footer": branding.get("credit_debit_footer"),
        "load_confirmation_footer": branding.get("load_confirmation_footer"),
        "carrier_invoice_footer": branding.get("carrier_invoice_footer"),
        "contract_footer": branding.get("contract_footer"),
        "pod_footer": branding.get("pod_footer"),
        "packing_list_footer": branding.get("packing_list_footer"),
        "grn_footer": branding.get("grn_footer"),
    }


def _get_document_categories_summary() -> dict[str, list[dict[str, str]]]:
    """Get summary of document types by category.

    Returns a mapping of category -> list of objects with `key`, `label`, and
    `description`.
    """
    categories = {
        "client": [],
        "carrier": [],
        "operational": [],
    }
    
    for doc_type in get_all_document_types():
        categories[doc_type.category.value].append(
            {
                "key": doc_type.key,
                "label": doc_type.label,
                "description": doc_type.description,
            }
        )
    
    return categories


@router.get("/branding", response_model=BrandingResponse)
async def get_branding(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Get current tenant branding settings."""
    branding_data = _extract_branding_from_settings(tenant)
    branding_data["document_categories"] = _get_document_categories_summary()
    
    return BrandingResponse(**branding_data)


@router.put("/branding", response_model=BrandingResponse)
async def update_branding(
    body: CompanyBranding,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant branding settings."""
    settings = tenant.settings or {}
    
    # Update company details at top level — only overwrite when the value is
    # non-empty so that partial saves (e.g. onboarding step 3) don't clobber
    # fields already populated in earlier steps.
    if body.name is not None:
        tenant.name = body.name
    if body.address is not None and body.address != "":
        settings["address"] = body.address
    if body.city is not None and body.city != "":
        settings["city"] = body.city
    if body.postal_code is not None and body.postal_code != "":
        settings["postal_code"] = body.postal_code
    if body.country is not None and body.country != "":
        settings["country"] = body.country
    if body.phone is not None and body.phone != "":
        settings["phone"] = body.phone
    if body.email is not None and body.email != "":
        settings["email"] = body.email
    if body.website is not None and body.website != "":
        settings["website"] = body.website
    if body.registration_number is not None and body.registration_number != "":
        settings["registration_number"] = body.registration_number
    if body.tax_number is not None and body.tax_number != "":
        settings["tax_number"] = body.tax_number
    
    # Update branding settings
    branding = settings.get("branding", {})
    if body.logo_storage_key is not None:
        branding["logo_storage_key"] = body.logo_storage_key
    if body.primary_color is not None:
        branding["primary_color"] = body.primary_color
    if body.secondary_color is not None:
        branding["secondary_color"] = body.secondary_color
    if body.footer_text is not None:
        branding["footer_text"] = body.footer_text
    
    # Update document-specific footers
    footer_fields = [
        "quotation_footer", "proforma_footer", "booking_footer",
        "invoice_footer", "credit_debit_footer", "load_confirmation_footer",
        "carrier_invoice_footer", "contract_footer", "pod_footer",
        "packing_list_footer", "grn_footer",
    ]
    for field in footer_fields:
        value = getattr(body, field)
        if value is not None:
            branding[field] = value
    
    settings["branding"] = branding
    tenant.settings = settings
    flag_modified(tenant, "settings")
    
    await db.flush()
    await db.commit()
    
    # Return updated branding
    branding_data = _extract_branding_from_settings(tenant)
    branding_data["document_categories"] = _get_document_categories_summary()
    
    return BrandingResponse(**branding_data)


@router.post("/branding/logo", status_code=status.HTTP_201_CREATED)
async def upload_logo(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload company logo."""
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size: 2MB"
        )
    
    # Upload to storage
    svc = DocumentService(db)
    doc = await svc.upload(
        tenant_id=tenant.id,
        file_content=content,
        filename=f"logo_{file.filename}",
        mime_type=file.content_type,
        doc_type="company_logo",
        uploaded_by=user.id,
    )
    
    # Update tenant branding with logo key
    settings = tenant.settings or {}
    branding = settings.get("branding", {})
    branding["logo_storage_key"] = doc.storage_key
    settings["branding"] = branding
    tenant.settings = settings
    flag_modified(tenant, "settings")
    await db.flush()
    await db.commit()
    
    return {"storage_key": doc.storage_key, "message": "Logo uploaded successfully"}


@router.delete("/branding/logo")
async def delete_logo(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete company logo."""
    settings = tenant.settings or {}
    branding = settings.get("branding", {})
    
    if "logo_storage_key" in branding:
        del branding["logo_storage_key"]
        settings["branding"] = branding
        tenant.settings = settings
        flag_modified(tenant, "settings")
        await db.flush()
        await db.commit()
    
    return {"message": "Logo removed successfully"}


@router.get("/branding/document-types")
async def get_document_types(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Get all available document types with their categories."""
    return _get_document_categories_summary()


# ── Onboarding ──────────────────────────────────────


class OnboardingStatusResponse(BaseModel):
    """Response with onboarding status."""
    onboarding_completed: bool
    company_details_completed: bool

    model_config = {"from_attributes": True}


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Check if tenant has completed onboarding."""
    settings = tenant.settings or {}
    company_details_completed = bool(
        settings.get("address")
        and settings.get("city")
        and settings.get("country")
        and settings.get("phone")
    )

    return OnboardingStatusResponse(
        onboarding_completed=tenant.onboarding_completed,
        company_details_completed=company_details_completed,
    )


@router.post("/onboarding/complete", response_model=OnboardingStatusResponse)
async def complete_onboarding(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark onboarding as completed."""
    settings = tenant.settings or {}
    required_fields = ["address", "city", "country", "phone"]
    missing_fields = [
        field for field in required_fields if not settings.get(field)
    ]

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Company details must be completed before finishing onboarding. "
                f"Missing: {', '.join(missing_fields)}"
            ),
        )

    tenant.onboarding_completed = True
    await db.flush()
    await db.commit()

    return OnboardingStatusResponse(
        onboarding_completed=True,
        company_details_completed=True,
    )


# ── Bank Accounts ─────────────────────────────────────


class BankAccountSchema(BaseModel):
    """A single saved bank account."""
    id: str
    bankName: str
    accountHolder: str
    accountNumber: str
    accountType: str | None = None
    branchName: str | None = None
    branchCode: str | None = None
    swiftCode: str | None = None


class BankAccountsResponse(BaseModel):
    """Response with saved bank accounts."""
    accounts: list[BankAccountSchema]


class BankAccountsUpdateRequest(BaseModel):
    """Request to replace all bank accounts."""
    accounts: list[BankAccountSchema]


@router.get("/bank-accounts", response_model=BankAccountsResponse)
async def get_bank_accounts(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Get saved bank accounts for this tenant."""
    settings = tenant.settings or {}
    raw = settings.get("bank_accounts", [])
    accounts = [BankAccountSchema(**a) for a in raw]
    return BankAccountsResponse(accounts=accounts)


@router.put("/bank-accounts", response_model=BankAccountsResponse)
async def update_bank_accounts(
    body: BankAccountsUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Replace all bank accounts for this tenant."""
    settings = tenant.settings or {}
    settings["bank_accounts"] = [a.model_dump() for a in body.accounts]
    tenant.settings = settings
    flag_modified(tenant, "settings")
    await db.flush()
    await db.commit()
    return BankAccountsResponse(accounts=body.accounts)

