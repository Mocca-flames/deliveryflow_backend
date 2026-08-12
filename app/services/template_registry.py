"""
Document Template Registry — Loads YAML templates, provides dynamic prompt building.

Templates define fields, validation rules, and visual hints for each document type.
Admins can add/tune templates via API without code changes.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "document_templates"


# ---------------------------------------------------------------------------
# Pydantic models for template structure
# ---------------------------------------------------------------------------

class FieldValidation(BaseModel):
    type: str  # not_expired, id_checksum, range, equals, regex, custom
    message: str = ""
    min: float | None = None
    max: float | None = None
    value: Any = None
    pattern: str = ""


class TemplateField(BaseModel):
    name: str
    type: str = "string"  # string, number, date, boolean, list
    required: bool = False
    pattern: str = ""
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    allowed_values: list[str] = Field(default_factory=list)
    format: str = ""  # for dates: YYYY-MM-DD
    validation: list[FieldValidation] = Field(default_factory=list)


class DocumentTemplate(BaseModel):
    doc_type: str
    category: str  # driver_pack, pod, border, commercial, transport, customs, permit, insurance
    label: str
    description: str = ""
    version: int = 1
    confidence_threshold: float = 0.7
    fields: list[TemplateField] = Field(default_factory=list)
    visual_hints: str = ""
    custom_prompt_addition: str = ""  # Admin can add extra prompt instructions


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TemplateRegistry:
    """Singleton registry for document templates."""

    def __init__(self) -> None:
        self._templates: dict[str, DocumentTemplate] = {}
        self._loaded = False

    def load_from_disk(self) -> int:
        """Load all YAML templates from document_templates/ directory."""
        count = 0
        if not TEMPLATES_DIR.exists():
            logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
            return 0

        for yaml_file in sorted(TEMPLATES_DIR.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                template = DocumentTemplate(**data)
                self._templates[template.doc_type] = template
                count += 1
                logger.debug(f"Loaded template: {template.doc_type}")
            except Exception as e:
                logger.error(f"Failed to load template {yaml_file.name}: {e}")

        self._loaded = True
        logger.info(f"Loaded {count} document templates")
        return count

    def get(self, doc_type: str) -> DocumentTemplate | None:
        """Get template by doc_type."""
        if not self._loaded:
            self.load_from_disk()
        return self._templates.get(doc_type)

    def get_all(self) -> dict[str, DocumentTemplate]:
        """Get all templates."""
        if not self._loaded:
            self.load_from_disk()
        return dict(self._templates)

    def get_by_category(self, category: str) -> list[DocumentTemplate]:
        """Get all templates for a category."""
        if not self._loaded:
            self.load_from_disk()
        return [t for t in self._templates.values() if t.category == category]

    def add_or_update(self, template: DocumentTemplate) -> None:
        """Add or update a template (admin operation)."""
        self._templates[template.doc_type] = template
        self._save_to_disk(template)
        logger.info(f"Template added/updated: {template.doc_type}")

    def delete(self, doc_type: str) -> bool:
        """Delete a template (admin operation)."""
        if doc_type in self._templates:
            del self._templates[doc_type]
            yaml_file = TEMPLATES_DIR / f"{doc_type.lower()}.yaml"
            if yaml_file.exists():
                yaml_file.unlink()
            logger.info(f"Template deleted: {doc_type}")
            return True
        return False

    def _save_to_disk(self, template: DocumentTemplate) -> None:
        """Save template to YAML file."""
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        yaml_file = TEMPLATES_DIR / f"{template.doc_type.lower()}.yaml"
        data = template.model_dump()
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def reload(self) -> int:
        """Force reload all templates from disk."""
        self._templates.clear()
        self._loaded = False
        return self.load_from_disk()


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_extraction_prompt(
    template: DocumentTemplate,
    extra_instructions: str = "",
) -> str:
    """Build a dynamic LLM extraction prompt from a template."""
    fields_desc = []
    for f in template.fields:
        req = "REQUIRED" if f.required else "optional"
        desc = f"  - {f.name}: {f.description} [{req}]"
        if f.type == "date" and f.format:
            desc += f" (format: {f.format})"
        if f.allowed_values:
            desc += f" (values: {', '.join(f.allowed_values)})"
        if f.examples:
            desc += f" (examples: {', '.join(f.examples[:3])})"
        fields_desc.append(desc)

    fields_text = "\n".join(fields_desc)

    # Build the allowed doc_type list
    doc_type_list = template.doc_type

    prompt = f"""You are an OCR assistant for freight and logistics documents.
Analyze the image and extract structured data from this {template.label}.

IMPORTANT: This document is a {template.label}. Extract the following fields:

{fields_text}

{template.visual_hints}

{template.custom_prompt_addition}

{extra_instructions}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "doc_type": "{doc_type_list}",
  "confidence": 0.0-1.0,
  "fields": {{ /* extracted field values */ }},
  "summary": "single-line summary with emoji"
}}"""

    return prompt


def build_auto_detect_prompt() -> str:
    """Build a prompt for auto-detecting document type."""
    return """You are an OCR assistant for freight and logistics documents.
Analyze the image and identify the document type.

Possible document types:
- VEHICLE_LICENCE: Motor vehicle licence/roadworthiness
- DRIVERS_LICENCE: SA driver's licence card
- ID_DOCUMENT: SA ID card or book
- INSURANCE_LETTER: Insurance confirmation letter
- POD_PHOTO: Proof of delivery photo
- POD_DOCUMENT: Signed delivery note/waybill
- CROSS_BORDER_PERMIT: CBRTA or cross-border transport permit
- CUSTOMS_DECLARATION: SAD 500, export/import declaration
- COMESA_YELLOW_CARD: COMESA motor vehicle insurance
- TRANSIT_BOND: Transit bond/guarantee
- CERTIFICATE_OF_ORIGIN: SADC/COMESA certificate of origin

Return ONLY valid JSON:
{
  "doc_type": "detected type or UNKNOWN",
  "confidence": 0.0-1.0,
  "fields": { /* all visible key-value pairs */ },
  "summary": "single-line summary with emoji"
}"""


# ---------------------------------------------------------------------------
# Response Validator
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    field_results: dict[str, dict[str, Any]] = Field(default_factory=dict)


def validate_extraction(
    result: dict[str, Any],
    template: DocumentTemplate,
) -> ValidationResult:
    """Validate LLM extraction result against template schema."""
    errors = []
    warnings = []
    field_results = {}

    fields = result.get("fields", {})
    confidence = result.get("confidence", 0.0)

    # Check confidence threshold
    if confidence < template.confidence_threshold:
        warnings.append(
            f"Low confidence: {confidence:.2f} < {template.confidence_threshold}"
        )

    # Validate each field
    for field_def in template.fields:
        value = fields.get(field_def.name)
        field_result: dict[str, Any] = {"present": value is not None}

        if field_def.required and value is None:
            errors.append(f"Missing required field: {field_def.name}")
            field_result["error"] = "missing_required"
        elif value is not None:
            # Type validation
            if field_def.type == "string" and not isinstance(value, str):
                try:
                    value = str(value)
                    fields[field_def.name] = value
                except (ValueError, TypeError):
                    errors.append(f"Field '{field_def.name}' must be a string")
                    field_result["error"] = "invalid_type"

            elif field_def.type == "number":
                try:
                    num_val = float(str(value).replace(",", "").replace(" ", ""))
                    fields[field_def.name] = num_val
                    value = num_val
                except (ValueError, TypeError):
                    errors.append(f"Field '{field_def.name}' must be a number")
                    field_result["error"] = "invalid_type"

            elif field_def.type == "boolean":
                if isinstance(value, str):
                    fields[field_def.name] = value.lower() in ("true", "yes", "1")
                    value = fields[field_def.name]

            elif field_def.type == "list":
                if isinstance(value, str):
                    fields[field_def.name] = [v.strip() for v in value.split(",")]
                    value = fields[field_def.name]
                elif not isinstance(value, list):
                    fields[field_def.name] = [value]
                    value = fields[field_def.name]

            # Pattern validation
            if field_def.pattern and isinstance(value, str):
                if not re.match(field_def.pattern, value):
                    errors.append(
                        f"Field '{field_def.name}' doesn't match pattern: {field_def.pattern}"
                    )
                    field_result["error"] = "pattern_mismatch"

            # Allowed values validation
            if field_def.allowed_values and value is not None:
                check_value = value if isinstance(value, str) else str(value)
                if check_value not in field_def.allowed_values:
                    warnings.append(
                        f"Field '{field_def.name}' value '{check_value}' not in allowed values"
                    )

            # Run custom validations
            for validation in field_def.validation:
                _run_validation(validation, field_def.name, value, errors, warnings)

            field_result["value"] = value

        field_results[field_def.name] = field_result

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        field_results=field_results,
    )


def _run_validation(
    validation: FieldValidation,
    field_name: str,
    value: Any,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Run a single validation rule."""
    if validation.type == "not_expired":
        if isinstance(value, str):
            try:
                exp = datetime.fromisoformat(value).date()
                if exp < date.today():
                    errors.append(validation.message or f"{field_name} has expired")
            except ValueError:
                warnings.append(f"Could not parse date: {value}")

    elif validation.type == "id_checksum":
        if isinstance(value, str) and len(value) == 13 and value.isdigit():
            digits = [int(d) for d in value]
            odd_sum = sum(digits[0::2])
            even_sum = sum(digits[1::2])
            total = odd_sum + 3 * even_sum
            if total % 10 != 0:
                errors.append(validation.message or f"Invalid ID checksum: {value}")

    elif validation.type == "range":
        try:
            num = float(str(value).replace(",", "").replace(" ", ""))
            if validation.min is not None and num < validation.min:
                errors.append(validation.message or f"{field_name} below minimum")
            if validation.max is not None and num > validation.max:
                errors.append(validation.message or f"{field_name} above maximum")
        except (ValueError, TypeError):
            pass

    elif validation.type == "equals":
        if value != validation.value:
            errors.append(validation.message or f"{field_name} != {validation.value}")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_registry: TemplateRegistry | None = None


def get_registry() -> TemplateRegistry:
    """Get or create singleton registry."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
        _registry.load_from_disk()
    return _registry
