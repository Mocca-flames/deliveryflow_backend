# DeliveryFlow — Backend PLAN.md (Open-Source First)

**Scope:** FastAPI service — Postgres RLS schema, Quotation/Contract/Billing + milestone state machine, tokenized link auth, NotificationDispatcher interface, API surface for Admin/Flutter/tracking links.

**Phase 1 only.** References [MASTER_PLAN.md](../MASTER_PLAN.md) for shared domain decisions.

**Strategy:** Use open-source libraries and existing code. Do NOT build from scratch what already exists.

---

## 1. What's Already Built (DO NOT REBUILD)

| Module | Status | Notes |
|--------|--------|-------|
| `app/main.py` | **DONE** | FastAPI app factory, CORS, route mounting |
| `app/config.py` | **DONE** | Pydantic Settings, all env vars, email service config |
| `app/deps.py` | **DONE** | JWT auth, tenant extraction, role checks, email router |
| `app/models/*` | **DONE** | All 12 ORM models (User, Tenant, Trip, Invoice, etc.) |
| `app/schemas/*` | **DONE** | All Pydantic v2 request/response schemas |
| `app/state_machines/*` | **DONE** | Invoice milestone + Driver's Pack state machines |
| `app/core/*` | **DONE** | Token gen, currency validation, SADC doc registry, exceptions |
| `app/notifications/*` | **DONE** | Abstract notifier + console adapter + dispatcher |
| `app/notifications/email/*` | **DONE** | Brevo + Mailjet adapters, EmailRouter with random selection + depletion fallback |
| `app/services/otp.py` | **DONE** | OTP generation, verification, email sending |
| `app/storage/*` | **DONE** | SeaweedFS S3 adapter |

---

## 2. Open-Source Libraries (Phase 1 Dependencies)

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing deps ...
    "weasyprint>=69.0",          # PDF generation from HTML/CSS
    "jinja2>=3.1.0",            # HTML templates for documents
    "python-multipart>=0.0.9",  # File uploads (already there)
    "paddleocr>=2.9.0",         # OCR for Driver's Pack (from reference_copy)
    "paddlepaddle>=2.6.0",      # PaddleOCR backend
    "pillow>=10.0.0",           # Image preprocessing for OCR
]
```

### Why These Libraries

| Library | Purpose | Why Not Build From Scratch |
|---------|---------|---------------------------|
| **WeasyPrint** | PDF generation | 9.4K stars, CSS Paged Media support, HTML/CSS templates = designer-friendly |
| **Jinja2** | Template rendering | Industry standard, works with WeasyPrint, already used in FastAPI ecosystem |
| **PaddleOCR** | Document OCR | Existing working pipeline in `reference_copy/` — reuse, don't rebuild |
| **Pillow** | Image preprocessing | Already used in reference_copy OCR pipeline |

---

## 3. New Directory Structure (Additions Only)

```
backend/
├── app/
│   ├── services/                    # NEW — Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py                  # Login, token refresh, password hashing
│   │   ├── otp.py                   # OTP generation, verification, email sending
│   │   ├── trip.py                  # Trip lifecycle operations
│   │   ├── invoice.py               # Invoice operations + milestone transitions
│   │   ├── document.py              # Upload, storage, retrieval
│   │   ├── drivers_pack.py          # KYC orchestration (uses reference_copy OCR)
│   │   ├── pdf_generator.py         # WeasyPrint PDF service
│   │   └── notification.py          # Notification dispatch wrapper
│   │
│   ├── notifications/               # NEW — Pluggable notifier adapters
│   │   ├── __init__.py
│   │   ├── base.py                  # Abstract Notifier interface
│   │   ├── console.py               # Console adapter (dev/debug)
│   │   ├── whatsapp.py              # Meta Cloud API adapter (Phase 2)
│   │   ├── sms.py                   # SMS adapter (stub for future)
│   │   └── email/                   # Dual-provider email (Brevo + Mailjet)
│   │       ├── __init__.py
│   │       ├── base.py              # Abstract EmailProvider + QuotaExceededError
│   │       ├── brevo.py             # Brevo API v3 adapter
│   │       ├── mailjet.py           # Mailjet API v3 adapter
│   │       └── router.py            # EmailRouter — random selection + depletion fallback
│   │
│   ├── templates/                   # NEW — Jinja2 HTML templates for PDFs
│   │   ├── base.html                # Base layout (header, footer, CSS)
│   │   ├── invoice.html             # Invoice PDF template
│   │   ├── quotation.html           # Quotation PDF template
│   │   ├── contract.html            # Contract PDF template
│   │   ├── waybill.html             # Road waybill template
│   │   └── css/
│   │       └── document.css         # Shared CSS (Paged Media, typography)
│   │
│   ├── ocr/                         # NEW — OCR integration (adapted from reference_copy)
│   │   ├── __init__.py
│   │   ├── engine.py                # PaddleOCR wrapper
│   │   ├── preprocessor.py          # Image preprocessing
│   │   ├── pipeline.py              # Two-stage OCR pipeline
│   │   ├── detector.py              # Document type detection
│   │   ├── parsing/                 # Field extraction per doc type
│   │   │   ├── __init__.py
│   │   │   ├── patterns.py          # Regex patterns
│   │   │   ├── licence.py           # SA driver licence parsing
│   │   │   ├── vehicle.py           # Vehicle licence parsing
│   │   │   └── permit.py            # Cross-border permit parsing
│   │   └── validation/              # Document validation rules
│   │       ├── __init__.py
│   │       ├── rules.py             # Permit validation
│   │       ├── vehicle.py           # Vehicle validation
│   │       └── licence.py           # Licence validation
│   │
│   ├── api/v1/                      # EXISTING — implement stubs
│   │   ├── auth.py                  # Login, refresh, register, verify-otp, resend-otp, forgot-password, reset-password, me
│   │   ├── trips.py                 # Wire up trip CRUD + lifecycle
│   │   ├── invoices.py              # Wire up invoice ops + PDF download
│   │   ├── drivers_packs.py         # Wire up KYC submission + review
│   │   ├── documents.py             # Wire up upload/download
│   │   ├── sync.py                  # Wire up Flutter outbox
│   │   └── router.py                # Add new routes
│   │
│   └── api/public/                  # EXISTING — implement stubs
│       ├── tracking.py              # Public tracking link
│       └── transporter_portal.py    # Transporter portal
│
├── tests/
│   ├── test_services/
│   ├── test_api/
│   └── test_ocr/
```

---

## 4. Phase 1 Implementation Roadmap

### Step 1: Install Dependencies + Docker Setup

```bash
# Add to pyproject.toml
pip install weasyprint jinja2 paddleocr paddlepaddle pillow

# Docker: add system deps for WeasyPrint
# Dockerfile additions:
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-1.0-0 libffi-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Step 2: PDF Generation Service

**File: `app/services/pdf_generator.py`**

```python
import asyncio
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

class PDFGenerator:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR))
        )

    async def generate_invoice(self, data: dict) -> bytes:
        template = self.env.get_template("invoice.html")
        html = template.render(**data)
        return await asyncio.to_thread(
            lambda: HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        )

    async def generate_quotation(self, data: dict) -> bytes:
        template = self.env.get_template("quotation.html")
        html = template.render(**data)
        return await asyncio.to_thread(
            lambda: HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        )

    async def generate_contract(self, data: dict) -> bytes:
        template = self.env.get_template("contract.html")
        html = template.render(**data)
        return await asyncio.to_thread(
            lambda: HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        )

    async def generate_waybill(self, data: dict) -> bytes:
        template = self.env.get_template("waybill.html")
        html = template.render(**data)
        return await asyncio.to_thread(
            lambda: HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        )

pdf_generator = PDFGenerator()
```

### Step 3: HTML/CSS Templates

**Reference Projects for Templates:**
- [federicodeponte/openword](https://github.com/federicodeponte/openword) — Pre-built invoice, contract, quotation HTML templates
- [markovskiL/pdf-generation](https://github.com/markovskiL/pdf-generation) — WeasyPrint template examples
- [rehborn/invoice-api](https://github.com/rehborn/invoice-api) — FastAPI + WeasyPrint invoice template

**Template structure (`app/templates/`):**

```html
<!-- base.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="css/document.css">
</head>
<body>
    <header>
        <div class="company-logo">{{ company.name }}</div>
        <div class="document-title">{{ document_type }}</div>
    </header>

    <section class="parties">
        <div class="from">{{ company | address_block }}</div>
        <div class="to">{{ client | address_block }}</div>
    </section>

    <section class="details">
        <table class="line-items">
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item.description }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ item.unit_price | currency }}</td>
                    <td>{{ item.amount | currency }}</td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr class="total">
                    <td colspan="3">Total ({{ currency }})</td>
                    <td>{{ total | currency }}</td>
                </tr>
            </tfoot>
        </table>
    </section>

    <footer>
        <div class="payment-terms">{{ payment_terms }}</div>
        <div class="page-number">Page <span class="page-number"></span></div>
    </footer>
</body>
</html>
```

**CSS with Paged Media (`app/templates/css/document.css`):**

```css
@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10px;
        color: #666;
    }
    @top-right {
        content: "{{ document_number }}";
        font-size: 10px;
        color: #999;
    }
}

body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #333;
}

.company-logo {
    font-size: 24pt;
    font-weight: bold;
    color: #2c5aa0;
}

.document-title {
    font-size: 18pt;
    font-weight: bold;
    margin: 1em 0;
}

table.line-items {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}

table.line-items th,
table.line-items td {
    padding: 8px;
    border-bottom: 1px solid #ddd;
    text-align: left;
}

table.line-items tfoot td {
    font-weight: bold;
    border-top: 2px solid #333;
}
```

### Step 4: OCR Integration (Adapt from reference_copy)

**Source:** `reference_copy/driverspack_whatsapp/apex-whatsapp/python_app/`

**Adaptation plan:**

| Reference File | Destination | Changes Needed |
|----------------|-------------|----------------|
| `ocr/engine.py` | `app/ocr/engine.py` | Keep as-is (PaddleOCR wrapper) |
| `ocr/preprocessor.py` | `app/ocr/preprocessor.py` | Keep as-is (Pillow preprocessing) |
| `ocr/pipeline.py` | `app/ocr/pipeline.py` | Keep as-is (two-stage pipeline) |
| `parsing/detector.py` | `app/ocr/detector.py` | Keep as-is (doc type detection) |
| `parsing/patterns.py` | `app/ocr/parsing/patterns.py` | Keep as-is (regex patterns) |
| `parsing/*.py` | `app/ocr/parsing/` | Keep as-is (field extraction) |
| `validation/*.py` | `app/ocr/validation/` | Keep as-is (validation rules) |
| `service.py` | `app/services/drivers_pack.py` | Adapt to use FastAPI DB sessions instead of standalone |

**Key adaptation — `service.py` → `services/drivers_pack.py`:**

```python
# Adapted from reference_copy service.py
# Changes: Use SQLAlchemy async sessions instead of standalone calls

from app.ocr.pipeline import run_ocr_pipeline
from app.ocr.validation.rules import validate_permit
from app.ocr.validation.vehicle import validate_vehicle
from app.ocr.validation.licence import validate_licence

async def verify_drivers_pack_document(
    image_bytes: bytes,
    doc_type: str,
    db: AsyncSession
) -> dict:
    """Verify a Driver's Pack document using OCR pipeline."""
    # Run OCR pipeline (adapted from reference_copy)
    ocr_result = await asyncio.to_thread(
        run_ocr_pipeline, image_bytes
    )

    # Validate based on document type
    if doc_type == "vehicle_licence":
        validation = validate_vehicle(ocr_result)
    elif doc_type == "drivers_licence":
        validation = validate_licence(ocr_result)
    elif doc_type in ("cross_border_permit", "temporary_import_permit"):
        validation = validate_permit(ocr_result)
    else:
        validation = {"valid": False, "error": "Unknown doc type"}

    return {
        "ocr_result": ocr_result,
        "validation": validation,
        "confidence": ocr_result.get("confidence", 0.0),
    }
```

### Step 5: Implement API Stubs (Wire Up Real Logic)

**Priority order for Phase 1:**

#### 5.1 Auth (`api/v1/auth.py`)
```python
# Use existing deps.py get_current_user pattern
# Implement real login with passlib password verification
# Implement JWT token generation with python-jose
```

#### 5.2 Trips CRUD (`api/v1/trips.py`)
```python
# Wire up SQLAlchemy queries using existing Trip model
# Implement list (with pagination), create, get, update
# Implement lifecycle actions: send-quotation, award-contract, assign, begin-transit, complete, cancel
```

#### 5.3 Invoices (`api/v1/invoices.py`)
```python
# Wire up Invoice model queries
# Implement issue (triggers 70/30 split calculation)
# Implement verify-pod (HITL trigger)
# Add PDF download endpoint: GET /invoices/{id}/pdf
```

#### 5.4 Documents (`api/v1/documents.py`)
```python
# Wire up file upload to SeaweedFS via storage.seaweed
# Wire up document metadata to Document model
# Implement pre-signed download URLs
```

#### 5.5 Driver's Packs (`api/v1/drivers_packs.py`)
```python
# Wire up OCR verification using adapted reference_copy pipeline
# Implement submit (triggers OCR auto-verify)
# Implement admin clear/flag actions
# Implement review queue (flagged packs)
```

### Step 6: Background Tasks

**File: `app/tasks/worker.py`** (expand existing)

```python
from taskiq import TaskiqRedisBroker

broker = TaskiqRedisBroker(url="redis://localhost:6379")

# Phase 1 tasks:
# 1. dispatch_notification — async send via NotificationDispatcher
# 2. revalidate_drivers_packs — daily cron, check expires_at
# 3. process_sync_events — validate, deduplicate, trigger state changes
# 4. check_invoice_overdue — daily cron, flag overdue invoices
```

### Step 7: Alembic Migrations

```bash
# Initialize Alembic
cd backend
alembic init app/migrations

# Generate first migration from models
alembic revision --autogenerate -m "initial schema"

# Apply
alembic upgrade head
```

---

## 5. Open-Source Reference Projects

### Document Generation

| Project | Tech | Use For |
|---------|------|---------|
| [federicodeponte/openword](https://github.com/federicodeponte/openword) | WeasyPrint + HTML/CSS | Pre-built invoice, contract, quotation templates |
| [rehborn/invoice-api](https://github.com/rehborn/invoice-api) | FastAPI + WeasyPrint | Working FastAPI invoice PDF endpoint |
| [markovskiL/pdf-generation](https://github.com/markovskiL/pdf-generation) | WeasyPrint + Jinja2 | Template examples and CSS patterns |
| [romamo/py-invoices](https://github.com/romamo/py-invoices) | WeasyPrint + Pydantic | Pluggable storage, Factur-X support |

### OCR / Driver's Pack

| Source | Use For |
|--------|---------|
| `reference_copy/driverspack_whatsapp/apex-whatsapp/python_app/` | **Primary source** — OCR pipeline, parsing, validation |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | OCR engine (already used in reference_copy) |

### Multi-Tenant SaaS Architecture

| Project | Use For |
|---------|---------|
| [rohteemie/multi-tenant-saas-backend](https://github.com/rohteemie/multi-tenant-saas-backend) | Architecture reference for billing SaaS |

---

## 6. API Endpoints — Implementation Priority

### Tier 1 (Must Have for Phase 1)

| Endpoint | Method | Implementation |
|----------|--------|----------------|
| `/api/v1/auth/login` | POST | Real JWT auth with passlib |
| `/api/v1/auth/refresh` | POST | Token refresh |
| `/api/v1/auth/me` | GET | Current user info |
| `/api/v1/auth/register` | POST | Create account + send verification OTP |
| `/api/v1/auth/verify-otp` | POST | Verify OTP + mark email verified |
| `/api/v1/auth/resend-otp` | POST | Resend verification OTP |
| `/api/v1/auth/forgot-password` | POST | Send password reset OTP |
| `/api/v1/auth/reset-password` | POST | Reset password with OTP |
| `/api/v1/trips/` | GET/POST | CRUD with pagination |
| `/api/v1/trips/{id}` | GET | Trip detail |
| `/api/v1/trips/{id}/award-contract` | POST | Award + validate driver pack |
| `/api/v1/invoices/{id}` | GET | Invoice detail |
| `/api/v1/invoices/{id}/issue` | POST | Issue + compute 70/30 |
| `/api/v1/invoices/{id}/pdf` | GET | **PDF download via WeasyPrint** |
| `/api/v1/documents/upload` | POST | Upload to SeaweedFS |
| `/api/v1/documents/{id}/download` | GET | Pre-signed URL |
| `/api/v1/drivers-packs/` | POST | Submit + OCR verification |
| `/api/v1/drivers-packs/queue` | GET | Admin review queue |

### Tier 2 (Important)

| Endpoint | Method | Implementation |
|----------|--------|----------------|
| `/api/v1/trips/{id}/send-quotation` | POST | Generate quotation PDF |
| `/api/v1/trips/{id}/assign` | POST | Assign transporter/driver/vehicle |
| `/api/v1/trips/{id}/begin-transit` | POST | Mark in transit |
| `/api/v1/trips/{id}/complete` | POST | Mark delivered |
| `/api/v1/invoices/{id}/verify-pod` | POST | HITL PoD verification |
| `/api/v1/drivers-packs/{id}/clear` | POST | Admin manual clearance |
| `/track/{token}` | GET | Public tracking data |
| `/transporter/{token}/accept` | POST | Transporter accepts trip |

### Tier 3 (Nice to Have)

| Endpoint | Method | Implementation |
|----------|--------|----------------|
| `/api/v1/sync/events` | POST | Flutter outbox sync |
| `/transporter/{token}/pod` | POST | PoD upload |
| `/transporter/{token}/border-docs` | POST | Border doc upload |

---

## 7. Document Types — PDF Generation Mapping

| Document | Template | Trigger | Data Source |
|----------|----------|---------|-------------|
| **Invoice** | `invoice.html` | `POST /invoices/{id}/issue` | Invoice + Trip models |
| **Quotation** | `quotation.html` | `POST /trips/{id}/send-quotation` | Trip model |
| **Contract** | `contract.html` | `POST /trips/{id}/award-contract` | Trip + Transporter models |
| **Road Waybill** | `waybill.html` | On trip `in_transit` | Trip + Document models |

---

## 8. Testing Strategy

```bash
# Unit tests (state machines, token gen, currency)
pytest tests/test_state_machines/ -v

# Service tests (PDF generation, OCR pipeline)
pytest tests/test_services/ -v

# API tests (endpoints with test DB)
pytest tests/test_api/ -m integration -v

# OCR tests (using sample images)
pytest tests/test_ocr/ -v
```

---

## 9. Docker Updates

**Dockerfile additions for WeasyPrint:**

```dockerfile
# System dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-1.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"
```

---

## 10. Implementation Order (Week 1-4)

### Week 1: Foundation
- [ ] Add WeasyPrint + Jinja2 to pyproject.toml
- [ ] Create `app/templates/` with base CSS
- [ ] Create `app/services/pdf_generator.py`
- [ ] Create `app/services/auth.py` (real JWT login)
- [ ] Initialize Alembic migrations

### Week 2: Core API
- [ ] Implement `api/v1/auth.py` (login, refresh)
- [ ] Implement `api/v1/trips.py` (CRUD + lifecycle)
- [ ] Implement `api/v1/invoices.py` (CRUD + issue + PDF download)
- [ ] Implement `api/v1/documents.py` (upload/download)

### Week 3: Document Generation
- [ ] Create invoice.html template
- [ ] Create quotation.html template
- [ ] Create contract.html template
- [ ] Create waybill.html template
- [ ] Wire PDF generation to API endpoints

### Week 4: OCR + Driver's Pack
- [ ] Adapt OCR pipeline from reference_copy
- [ ] Implement `api/v1/drivers_packs.py` (submit, verify, review)
- [ ] Implement background tasks (Taskiq)
- [ ] Public tracking + transporter portal endpoints

---

*This plan is the source of truth for backend implementation. Reference [MASTER_PLAN.md](../MASTER_PLAN.md) for shared domain decisions.*
