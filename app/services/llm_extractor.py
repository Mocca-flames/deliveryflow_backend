"""
Vision LLM Document Extractor — Template-driven, multi-provider pipeline.

Adapted from apex_ai-bot. Uses YAML templates for dynamic prompt building.
Providers: Mistral (primary) → Google Gemini (fallback) → OpenRouter (fallback)
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PIL import Image

from app.services.template_registry import (
    build_auto_detect_prompt,
    build_extraction_prompt,
    get_registry,
    validate_extraction,
    DocumentTemplate,
    ValidationResult,
)

load_dotenv()

logger = logging.getLogger(__name__)


def image_to_base64(image: Image.Image, max_size: int = 2000) -> str:
    """Convert PIL Image to base64 data URL, resizing if needed."""
    if max(image.size) > max_size:
        image = image.resize((max_size, max_size), Image.Resampling.LANCZOS)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

class _MistralProvider:
    def __init__(self, api_key: str, model: str):
        from mistralai.client import Mistral
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.name = "mistral"

    def call_vision(self, prompt: str, image_b64: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_b64}},
                ],
            }],
            max_tokens=1000,
            temperature=0.0,
            top_p=1,
        )
        return response.choices[0].message.content or ""


class _GoogleProvider:
    def __init__(self, api_key: str, model: str):
        from google.genai import Client
        self.client = Client(api_key=api_key)
        self.model = model
        self.name = "google"

    def call_vision(self, prompt: str, image_b64: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=[{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64.split(",")[1]}},
                ],
            }],
        )
        return response.text or ""


class _OpenRouterProvider:
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.model = model
        self.name = "openrouter"

    def call_vision(self, prompt: str, image_b64: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_b64}},
                ],
            }],
            max_tokens=1000,
            temperature=0.0,
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

PROVIDER_META: dict[str, tuple[str, str, str, type]] = {
    "mistral": ("MISTRAL_API_KEY", "MISTRAL_VISION_MODEL", "ministral-14b-latest", _MistralProvider),
    "google": ("GOOGLE_API_KEY", "GOOGLE_VISION_MODEL", "gemini-2.5-flash", _GoogleProvider),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini", _OpenRouterProvider),
}


class ExtractionResult:
    """Result of document extraction with validation."""

    def __init__(
        self,
        raw: dict[str, Any],
        template: DocumentTemplate | None = None,
        validation: ValidationResult | None = None,
    ):
        self.raw = raw
        self.template = template
        self.validation = validation

    @property
    def doc_type(self) -> str:
        return self.raw.get("doc_type", "UNKNOWN")

    @property
    def confidence(self) -> float:
        return self.raw.get("confidence", 0.0)

    @property
    def fields(self) -> dict[str, Any]:
        return self.raw.get("fields", {})

    @property
    def summary(self) -> str | None:
        return self.raw.get("summary")

    @property
    def is_valid(self) -> bool:
        return self.validation.valid if self.validation else True

    @property
    def errors(self) -> list[str]:
        return self.validation.errors if self.validation else []

    @property
    def warnings(self) -> list[str]:
        return self.validation.warnings if self.validation else []

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "confidence": self.confidence,
            "fields": self.fields,
            "summary": self.summary,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "template_version": self.template.version if self.template else None,
            "_provider": self.raw.get("_provider"),
            "_model": self.raw.get("_model"),
        }


class LLMDocumentExtractor:
    """Template-driven, multi-provider vision LLM extractor."""

    def __init__(self, log_dir: Path | str | None = None):
        self.providers: list[Any] = []
        self._healthy = False
        self._registry = get_registry()

        if log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_path = self.log_dir / "llm_calls.jsonl"
        else:
            self.log_path = None

        provider_order = os.getenv("LLM_PROVIDERS", "mistral,google").lower()
        provider_names = [p.strip() for p in provider_order.split(",") if p.strip()]

        for name in provider_names:
            if name not in PROVIDER_META:
                logger.warning(f"Unknown LLM provider '{name}' — skipping")
                continue
            key_env, model_env, default_model, cls = PROVIDER_META[name]
            api_key = os.getenv(key_env, "").strip()
            if not api_key:
                logger.info(f"Provider '{name}' skipped — {key_env} not set")
                continue
            model = os.getenv(model_env, default_model)
            try:
                provider = cls(api_key=api_key, model=model)
                self.providers.append(provider)
                logger.info(f"LLM provider '{name}' ready (model: {model})")
            except Exception as e:
                logger.error(f"Failed to init provider '{name}': {e}")

        if self.providers:
            self._healthy = True
        else:
            logger.error("No LLM providers configured — document extraction will fail")

    @property
    def healthy(self) -> bool:
        return self._healthy

    def health_check(self) -> bool:
        """Test first provider in order."""
        for prov in self.providers:
            try:
                result = prov.call_vision("Say 'OK' in one word.", "data:image/jpeg;base64,/9j/test")
                if any(w in result.lower() for w in ("ok", "hello", "hi")):
                    self._healthy = True
                    return True
            except Exception:
                continue
        self._healthy = False
        return False

    # -----------------------------------------------------------------------
    # Core extraction — template-driven
    # -----------------------------------------------------------------------

    def extract(
        self,
        image: Image.Image,
        doc_type: str | None = None,
        doc_category: str | None = None,
        extra_instructions: str = "",
    ) -> ExtractionResult:
        """Extract structured data from a document image.

        Args:
            image: PIL Image (RGB)
            doc_type: Specific doc type (e.g., "VEHICLE_LICENCE") — skips auto-detect
            doc_category: Category hint ("driver_pack", "pod", "border") for auto-detect
            extra_instructions: Additional prompt instructions from admin

        Returns:
            ExtractionResult with fields, validation, and metadata
        """
        # Get template if doc_type is specified
        template = None
        if doc_type:
            template = self._registry.get(doc_type)

        # Build prompt
        if template:
            prompt = build_extraction_prompt(template, extra_instructions)
        else:
            prompt = build_auto_detect_prompt()

        image_b64 = image_to_base64(image)

        # Try providers
        last_error = None
        for prov in self.providers:
            for attempt in range(3):
                try:
                    raw = prov.call_vision(prompt, image_b64)
                    result = self._parse_response(raw)
                    result["_provider"] = prov.name
                    result["_model"] = getattr(prov, "model", "unknown")

                    # If no template was provided, try to get one from detected doc_type
                    if template is None:
                        detected_type = result.get("doc_type", "UNKNOWN")
                        template = self._registry.get(detected_type)

                    # Validate against template
                    validation = None
                    if template:
                        validation = validate_extraction(result, template)

                    self._log_call(result)
                    return ExtractionResult(raw=result, template=template, validation=validation)

                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str:
                        if attempt < 2:
                            time.sleep(2.0 * (attempt + 1))
                            continue
                    elif "5" in err_str and ("error" in err_str or "unavailable" in err_str):
                        if attempt < 2:
                            time.sleep(2.0 * (attempt + 1))
                            continue
                    break

        logger.error(f"All LLM providers failed. Last error: {last_error}")
        error_raw = self._error_response("LLM_UNAVAILABLE", str(last_error))
        return ExtractionResult(raw=error_raw)

    async def extract_async(
        self,
        image: Image.Image,
        doc_type: str | None = None,
        doc_category: str | None = None,
        extra_instructions: str = "",
    ) -> ExtractionResult:
        """Async wrapper for extract()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.extract, image, doc_type, doc_category, extra_instructions
        )

    # -----------------------------------------------------------------------
    # Batch extraction
    # -----------------------------------------------------------------------

    async def extract_batch(
        self,
        images: list[tuple[str, Image.Image]],
        doc_type: str | None = None,
        doc_category: str | None = None,
        max_concurrent: int = 3,
    ) -> list[ExtractionResult]:
        """Extract from multiple images concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _process(label: str, img: Image.Image) -> ExtractionResult:
            async with semaphore:
                result = await self.extract_async(img, doc_type, doc_category)
                result.raw["_label"] = label
                return result

        tasks = [_process(label, img) for label, img in images]
        return await asyncio.gather(*tasks, return_exceptions=False)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse LLM JSON response."""
        cleaned = raw.strip()
        if cleaned.startswith("```json") and cleaned.endswith("```"):
            cleaned = cleaned[7:-3].strip()
        elif cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"LLM JSON parse error: {e}")
            return self._error_response("LLM_PARSE_ERROR", f"Invalid JSON: {e}")

        return {
            "doc_type": parsed.get("doc_type", "UNKNOWN"),
            "confidence": float(parsed.get("confidence", 0.0)),
            "fields": parsed.get("fields", {}),
            "summary": parsed.get("summary", ""),
            "rejection_flag": None,
        }

    def _log_call(self, record: dict[str, Any]) -> None:
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"LLM logging failed: {e}")

    def _error_response(self, flag: str, msg: str) -> dict[str, Any]:
        return {
            "doc_type": "UNKNOWN",
            "confidence": 0.0,
            "fields": {},
            "summary": None,
            "rejection_flag": flag,
            "_error": msg,
        }

    # -----------------------------------------------------------------------
    # Template management (admin)
    # -----------------------------------------------------------------------

    def reload_templates(self) -> int:
        """Force reload all templates from disk."""
        return self._registry.reload()

    def get_template(self, doc_type: str) -> DocumentTemplate | None:
        """Get a specific template."""
        return self._registry.get(doc_type)

    def get_all_templates(self) -> dict[str, DocumentTemplate]:
        """Get all templates."""
        return self._registry.get_all()


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------

def post_process_result(result: ExtractionResult) -> ExtractionResult:
    """Apply post-processing based on detected doc type."""
    fields = dict(result.fields)
    doc_type = result.doc_type

    if doc_type == "VEHICLE_LICENCE":
        if "reg" in fields and "reg_number" not in fields:
            fields["reg_number"] = fields.pop("reg")
        fields.setdefault("attention", "")
        expiry_str = fields.get("expiry_date")
        if expiry_str:
            try:
                exp = datetime.fromisoformat(expiry_str).date()
                today = date.today()
                fields["is_expired"] = exp < today
                fields["days_to_expiry"] = (exp - today).days
            except Exception:
                fields["is_expired"] = None
                fields["days_to_expiry"] = None

    elif doc_type == "INSURANCE_LETTER":
        legit = fields.get("is_legit")
        if isinstance(legit, str):
            fields["is_legit"] = legit.lower() == "true"
        elif not isinstance(legit, bool):
            fields["is_legit"] = False
        fields.setdefault("is_expired", False)

    result.raw["fields"] = fields
    return result


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_extractor: LLMDocumentExtractor | None = None


def get_extractor() -> LLMDocumentExtractor:
    """Get or create singleton extractor."""
    global _extractor
    if _extractor is None:
        base_dir = Path(__file__).resolve().parent.parent
        log_dir = base_dir / "data" / "llm_logs"
        _extractor = LLMDocumentExtractor(log_dir=log_dir)
    return _extractor
