"""
Admin API endpoints for document template management.

Allows admins to:
- List, create, update, delete document templates
- Test extraction with sample images
- View extraction logs and statistics
- Tune prompts and validation rules
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.deps import require_super_admin, get_current_user
from app.models.user import User
from app.services.template_registry import (
    DocumentTemplate,
    TemplateField,
    FieldValidation,
    get_registry,
)
from app.services.llm_extractor import get_extractor

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class FieldValidationSchema(BaseModel):
    type: str
    message: str = ""
    min: float | None = None
    max: float | None = None
    value: Any = None
    pattern: str = ""


class TemplateFieldSchema(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    pattern: str = ""
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    allowed_values: list[str] = Field(default_factory=list)
    format: str = ""
    validation: list[FieldValidationSchema] = Field(default_factory=list)


class TemplateCreateUpdate(BaseModel):
    doc_type: str
    category: str
    label: str
    description: str = ""
    version: int = 1
    confidence_threshold: float = 0.7
    fields: list[TemplateFieldSchema] = Field(default_factory=list)
    visual_hints: str = ""
    custom_prompt_addition: str = ""


class TemplateResponse(BaseModel):
    doc_type: str
    category: str
    label: str
    description: str
    version: int
    confidence_threshold: float
    field_count: int
    fields: list[dict[str, Any]]


class ExtractionTestResponse(BaseModel):
    doc_type: str
    confidence: float
    fields: dict[str, Any]
    summary: str | None
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    provider: str | None
    model: str | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(user: User = Depends(require_super_admin)):
    """List all document templates."""
    registry = get_registry()
    templates = registry.get_all()
    return [
        TemplateResponse(
            doc_type=t.doc_type,
            category=t.category,
            label=t.label,
            description=t.description,
            version=t.version,
            confidence_threshold=t.confidence_threshold,
            field_count=len(t.fields),
            fields=[f.model_dump() for f in t.fields],
        )
        for t in templates.values()
    ]


@router.get("/templates/{doc_type}", response_model=TemplateResponse)
async def get_template(doc_type: str, user: User = Depends(require_super_admin)):
    """Get a specific document template."""
    registry = get_registry()
    template = registry.get(doc_type)
    if not template:
        raise HTTPException(404, f"Template '{doc_type}' not found")
    return TemplateResponse(
        doc_type=template.doc_type,
        category=template.category,
        label=template.label,
        description=template.description,
        version=template.version,
        confidence_threshold=template.confidence_threshold,
        field_count=len(template.fields),
        fields=[f.model_dump() for f in template.fields],
    )


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    data: TemplateCreateUpdate,
    user: User = Depends(require_super_admin),
):
    """Create or update a document template."""
    registry = get_registry()

    # Check if exists
    existing = registry.get(data.doc_type)
    if existing:
        raise HTTPException(409, f"Template '{data.doc_type}' already exists. Use PUT to update.")

    template = DocumentTemplate(
        doc_type=data.doc_type,
        category=data.category,
        label=data.label,
        description=data.description,
        version=data.version,
        confidence_threshold=data.confidence_threshold,
        fields=[
            TemplateField(
                name=f.name,
                type=f.type,
                required=f.required,
                pattern=f.pattern,
                description=f.description,
                examples=f.examples,
                allowed_values=f.allowed_values,
                format=f.format,
                validation=[FieldValidation(**v.model_dump()) for v in f.validation],
            )
            for f in data.fields
        ],
        visual_hints=data.visual_hints,
        custom_prompt_addition=data.custom_prompt_addition,
    )

    registry.add_or_update(template)

    return TemplateResponse(
        doc_type=template.doc_type,
        category=template.category,
        label=template.label,
        description=template.description,
        version=template.version,
        confidence_threshold=template.confidence_threshold,
        field_count=len(template.fields),
        fields=[f.model_dump() for f in template.fields],
    )


@router.put("/templates/{doc_type}", response_model=TemplateResponse)
async def update_template(
    doc_type: str,
    data: TemplateCreateUpdate,
    user: User = Depends(require_super_admin),
):
    """Update an existing document template."""
    registry = get_registry()
    existing = registry.get(doc_type)
    if not existing:
        raise HTTPException(404, f"Template '{doc_type}' not found")

    template = DocumentTemplate(
        doc_type=data.doc_type,
        category=data.category,
        label=data.label,
        description=data.description,
        version=data.version,
        confidence_threshold=data.confidence_threshold,
        fields=[
            TemplateField(
                name=f.name,
                type=f.type,
                required=f.required,
                pattern=f.pattern,
                description=f.description,
                examples=f.examples,
                allowed_values=f.allowed_values,
                format=f.format,
                validation=[FieldValidation(**v.model_dump()) for v in f.validation],
            )
            for f in data.fields
        ],
        visual_hints=data.visual_hints,
        custom_prompt_addition=data.custom_prompt_addition,
    )

    registry.add_or_update(template)

    return TemplateResponse(
        doc_type=template.doc_type,
        category=template.category,
        label=template.label,
        description=template.description,
        version=template.version,
        confidence_threshold=template.confidence_threshold,
        field_count=len(template.fields),
        fields=[f.model_dump() for f in template.fields],
    )


@router.delete("/templates/{doc_type}")
async def delete_template(doc_type: str, user: User = Depends(require_super_admin)):
    """Delete a document template."""
    registry = get_registry()
    if not registry.get(doc_type):
        raise HTTPException(404, f"Template '{doc_type}' not found")

    registry.delete(doc_type)
    return {"message": f"Template '{doc_type}' deleted"}


@router.post("/templates/reload")
async def reload_templates(user: User = Depends(require_super_admin)):
    """Force reload all templates from disk."""
    extractor = get_extractor()
    count = extractor.reload_templates()
    return {"message": f"Reloaded {count} templates"}


@router.post("/templates/test", response_model=ExtractionTestResponse)
async def test_extraction(
    doc_type: str | None = None,
    file: UploadFile = File(...),
    user: User = Depends(require_super_admin),
):
    """Test document extraction with a sample image."""
    from io import BytesIO
    from PIL import Image

    contents = await file.read()
    try:
        image = Image.open(BytesIO(contents))
    except Exception:
        raise HTTPException(400, "Invalid image file")

    extractor = get_extractor()
    result = extractor.extract(image, doc_type=doc_type)

    return ExtractionTestResponse(
        doc_type=result.doc_type,
        confidence=result.confidence,
        fields=result.fields,
        summary=result.summary,
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
        provider=result.raw.get("_provider"),
        model=result.raw.get("_model"),
    )
