# DeliveryFlow — Backend PLAN.md

**Scope:** FastAPI service — Postgres RLS schema, Quotation/Contract/Invoice/Milestone state machine, tokenized link auth, NotificationDispatcher interface, API surface for Admin/Flutter/tracking links.

**Phase 1 only.** References [MASTER_PLAN.md](../MASTER_PLAN.md) for shared domain decisions.

---

## 1. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory, lifespan, middleware
│   ├── config.py                # Pydantic Settings (env-based config)
│   ├── deps.py                  # Dependency injection (get_db, get_current_user, get_tenant)
│   │
│   ├── models/                  # SQLAlchemy 2.0 ORM models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model, mixins (TimestampMixin, UUIDPrimaryKey)
│   │   ├── tenant.py            # Tenant (broker) model
│   │   ├── user.py              # User model (broker staff, platform admin)
│   │   ├── carrier.py           # Carrier (lightweight, under broker tenant)
│   │   ├── driver.py            # Driver (linked to carrier)
│   │   ├── vehicle.py           # Vehicle (linked to carrier)
│   │   ├── trip.py              # Trip/Contract (core entity)
│   │   ├── invoice.py           # Master Invoice (1:1 with trip)
│   │   ├── invoice_milestone.py # Milestone state transitions
│   │   ├── document.py          # Document references (uploaded files)
│   │   ├── drivers_pack.py      # Driver's Pack (KYC per driver/vehicle)
│   │   ├── sync_event.py        # Outbox sync events from Flutter
│   │   └── notification_log.py  # Notification audit trail
│   │
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   │   ├── __init__.py
│   │   ├── common.py            # Shared schemas (Pagination, ErrorResponse)
│   │   ├── auth.py              # Login, token refresh
│   │   ├── tenant.py
│   │   ├── carrier.py
│   │   ├── driver.py
│   │   ├── vehicle.py
│   │   ├── trip.py
│   │   ├── invoice.py
│   │   ├── document.py
│   │   ├── drivers_pack.py
│   │   └── sync.py              # Outbox sync schemas
│   │
│   ├── api/                     # Route modules
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # v1 API router aggregation
│   │   │   ├── auth.py          # POST /auth/login, /auth/refresh
│   │   │   ├── tenants.py       # CRUD (super-admin only)
│   │   │   ├── users.py         # CRUD (tenant-scoped)
│   │   │   ├── carriers.py      # CRUD under tenant
│   │   │   ├── drivers.py       # CRUD under tenant
│   │   │   ├── vehicles.py      # CRUD under tenant
│   │   │   ├── trips.py         # Full trip lifecycle
│   │   │   ├── invoices.py      # Invoice operations, milestone triggers
│   │   │   ├── documents.py     # Upload/download, pre-signed URLs
│   │   │   ├── drivers_packs.py # KYC submission, status, admin review
│   │   │   ├── sync.py          # Flutter outbox sync endpoint
│   │   │   └── notifications.py # Notification preferences, history
│   │   └── public/
│   │       ├── __init__.py
│   │       ├── tracking.py      # GET /track/{token} — public, no auth
│   │       └── carrier_portal.py # GET/POST /carrier/{token} — carrier actions
│   │
│   ├── core/                    # Domain logic, state machines
│   │   ├── __init__.py
│   │   ├── security.py          # JWT creation/verification, password hashing
│   │   ├── token.py             # Tokenized link generation/validation
│   │   ├── exceptions.py        # Custom exception classes
│   │   ├── events.py            # Event types for internal pub/sub
│   │   ├── currency.py          # Currency code validation (ZAR default, no logic yet)
│   │   └── documents/           # SADC cross-border document types (modular)
│   │       ├── __init__.py      # Public API — re-exports registry functions
│   │       ├── commercial.py    # Invoice, Packing List, Certificate of Origin, DG, Phytosanitary, Veterinary
│   │       ├── transport.py     # Road Waybill, CMR, Consignment Note, DA 187 Manifest
│   │       ├── customs.py       # SAD 500/502/505/507, Export/Import Declarations, Transit Bond, SRCTD
│   │       ├── permits.py       # CBRTA, SADC Driver Cert, PrDP, Import/Export Permits
│   │       ├── insurance.py     # COMESA Yellow Card, GIT Insurance, TIP
│   │       ├── driver_pack.py   # Vehicle Licence, Driver's Licence, ID, Insurance Letter
│   │       └── registry.py      # Central registry, route-aware requirements, SACU logic
│   │
│   ├── state_machines/          # Milestone & KYC state machines
│   │   ├── __init__.py
│   │   ├── invoice.py           # Invoice milestone state machine
│   │   └── drivers_pack.py      # Driver's Pack state machine
│   │
│   ├── services/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication service
│   │   ├── trip.py              # Trip lifecycle service
│   │   ├── invoice.py           # Invoice service (milestone transitions, 70/30 split)
│   │   ├── document.py          # Document upload, storage, retrieval
│   │   ├── drivers_pack.py      # KYC orchestration, LLM extraction trigger, review queue
│   │   ├── llm_extractor.py     # Vision LLM document extraction (Mistral/Gemini/OpenRouter)
│   │   ├── template_registry.py # Document template loader, prompt builder, validator
│   │   ├── notification.py      # NotificationDispatcher interface
│   │   ├── sync.py              # Outbox sync processing
│   │   └── tracking.py          # Tokenized tracking link data
│   │
│   ├── document_templates/      # YAML templates for LLM extraction (admin-configurable)
│   │   ├── vehicle_licence.yaml
│   │   ├── drivers_licence.yaml
│   │   ├── id_document.yaml
│   │   ├── insurance_letter.yaml
│   │   ├── pod_photo.yaml
│   │   ├── pod_document.yaml
│   │   ├── cross_border_permit.yaml
│   │   ├── customs_declaration.yaml
│   │   ├── comesa_yellow_card.yaml
│   │   ├── transit_bond.yaml
│   │   └── certificate_of_origin.yaml
│   │
│   ├── notifications/           # Pluggable notifier adapters
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract Notifier interface
│   │   ├── whatsapp.py          # Meta Cloud API adapter (Phase 2)
│   │   ├── sms.py               # SMS adapter (stub for future)
│   │   ├── email.py             # Email adapter (stub for future)
│   │   └── console.py           # Console adapter (dev/debug)
│   │
│   ├── storage/                 # Object storage abstraction
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract StorageBackend interface
│   │   └── seaweed.py           # SeaweedFS S3-compatible adapter
│   │
│   ├── tasks/                   # Taskiq background tasks
│   │   ├── __init__.py
│   │   ├── worker.py            # Taskiq worker config
│   │   ├── invoice.py           # Invoice scheduled tasks
│   │   ├── drivers_pack.py      # Pack expiry re-validation
│   │   ├── notifications.py     # Async notification dispatch
│   │   └── sync.py              # Sync event processing
│   │
│   └── migrations/              # Alembic migrations
│       ├── env.py
│       ├── versions/
│       └── script.py.mako
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Fixtures, test DB setup
│   ├── test_models/
│   ├── test_api/
│   ├── test_services/
│   ├── test_state_machines/
│   └── test_tasks/
│
├── alembic.ini
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml           # Local dev: postgres, redis, seaweed
├── .env.example
└── README.md
```

---

## 2. Tech Stack (Phase 1)

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy 2.0 | async (asyncpg) |
| Migrations | Alembic | latest |
| Validation | Pydantic v2 | latest |
| DB | PostgreSQL | 16+ |
| DB Driver | asyncpg | latest |
| Cache/Queue | Redis | 7+ |
| Task Queue | Taskiq + Taskiq-Redis | latest |
| Object Storage | SeaweedFS | S3-compatible API |
| Auth | JWT (jose) | RS256 |
| Document Extraction | Vision LLM (Mistral → Gemini → OpenRouter) | multi-provider |
| PDF Generation | WeasyPrint + Jinja2 | 69.0+ |
| Testing | pytest + pytest-asyncio | latest |
| Linting | Ruff | latest |
| Type Checking | mypy + pyright | latest |

---

## 3. Database Schema (PostgreSQL + RLS)

### 3.1 Multi-Tenancy via Row-Level Security

Every tenant-scoped table carries a `tenant_id` column. RLS policies enforce isolation:

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
-- ... etc

-- Policy: users can only see rows belonging to their tenant
CREATE POLICY tenant_isolation ON trips
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

The `app.current_tenant_id` session variable is set by the application on every connection:

```python
async def set_tenant_context(connection, tenant_id: uuid.UUID):
    await connection.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(tenant_id)}
    )
```

**Platform-level (super admin) bypass:** Set a session variable `app.is_super_admin = true` and adjust policies:

```sql
CREATE POLICY super_admin_bypass ON trips
    USING (current_setting('app.is_super_admin', true)::boolean = true);
```

### 3.2 Core Tables

```sql
-- ============================================================
-- TENANTS
-- ============================================================
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    settings        JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- USERS (broker staff, platform admin)
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),  -- NULL for super-admin
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('super_admin', 'tenant_admin', 'tenant_staff')),
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- CARRIERS (lightweight, under broker tenant)
-- ============================================================
CREATE TABLE carriers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            TEXT NOT NULL,
    contact_name    TEXT,
    contact_phone   TEXT,
    contact_email   TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- DRIVERS
-- ============================================================
CREATE TABLE drivers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    carrier_id      UUID NOT NULL REFERENCES carriers(id),
    full_name       TEXT NOT NULL,
    phone           TEXT,
    license_number  TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- VEHICLES
-- ============================================================
CREATE TABLE vehicles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    carrier_id      UUID NOT NULL REFERENCES carriers(id),
    registration    TEXT NOT NULL,
    make            TEXT,
    model           TEXT,
    year            INTEGER,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- TRIPS / CONTRACTS (core entity)
-- ============================================================
CREATE TABLE trips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    reference       TEXT NOT NULL,               -- Human-readable ref (e.g., "TRP-2026-001")
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN (
                        'draft',
                        'quotation_sent',
                        'contract_awarded',
                        'in_transit',
                        'border_clearance',
                        'delivered',
                        'pod_captured',
                        'pod_verified',
                        'completed',
                        'cancelled'
                    )),
    -- Parties
    carrier_id      UUID REFERENCES carriers(id),
    driver_id       UUID REFERENCES drivers(id),
    vehicle_id      UUID REFERENCES vehicles(id),
    -- Route
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    -- Client info (denormalized for Phase 1, separate Client entity later)
    client_name     TEXT,
    client_email    TEXT,
    client_phone    TEXT,
    -- Cargo
    cargo_desc      TEXT,
    cargo_weight_kg NUMERIC(10,2),
    -- Quotation
    quoted_amount   NUMERIC(12,2),
    currency        TEXT DEFAULT 'ZAR',          -- Per §4.4: always carry currency
    -- Contract
    contract_url    TEXT,                         -- URL to signed contract doc
    awarded_at      TIMESTAMPTZ,
    -- Dates
    pickup_date     DATE,
    delivery_date   DATE,
    -- Tokenized links
    tracking_token  TEXT UNIQUE,
    carrier_token   TEXT UNIQUE,
    -- Metadata
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, reference)
);

-- ============================================================
-- MASTER INVOICE (1:1 with trip)
-- ============================================================
CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    trip_id         UUID NOT NULL UNIQUE REFERENCES trips(id),
    invoice_number  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN (
                        'draft',
                        'issued',
                        'upfront_paid',
                        'balance_due',
                        'paid',
                        'overdue',
                        'cancelled'
                    )),
    -- Amounts
    total_amount    NUMERIC(12,2) NOT NULL,
    currency        TEXT DEFAULT 'ZAR',
    upfront_pct     NUMERIC(5,2) DEFAULT 70.00,  -- Phase 1: always 70%
    balance_pct     NUMERIC(5,2) DEFAULT 30.00,
    upfront_amount  NUMERIC(12,2),                -- Computed on issue
    balance_amount  NUMERIC(12,2),                -- Computed on issue
    -- Milestone tracking
    current_milestone TEXT DEFAULT 'none'
                    CHECK (current_milestone IN (
                        'none',
                        'upfront_requested',
                        'upfront_paid',
                        'in_transit',
                        'pod_captured',
                        'pod_verified',
                        'balance_released',
                        'fully_paid'
                    )),
    -- Dates
    issued_at       TIMESTAMPTZ,
    upfront_paid_at TIMESTAMPTZ,
    balance_paid_at TIMESTAMPTZ,
    -- Metadata
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INVOICE MILESTONES (event log — append only)
-- ============================================================
CREATE TABLE invoice_milestones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    invoice_id      UUID NOT NULL REFERENCES invoices(id),
    milestone       TEXT NOT NULL,
    from_status     TEXT,
    to_status       TEXT NOT NULL,
    triggered_by    UUID REFERENCES users(id),   -- NULL for system/automated
    trigger_source  TEXT DEFAULT 'manual'         -- 'manual', 'webhook', 'task', 'sync'
                    CHECK (trigger_source IN ('manual', 'webhook', 'task', 'sync')),
    notes           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- DOCUMENTS (uploaded files — SADC cross-border doc vault)
-- ============================================================
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    trip_id         UUID REFERENCES trips(id),
    drivers_pack_id UUID REFERENCES drivers_packs(id),
    doc_type        TEXT NOT NULL
                    CHECK (doc_type IN (
                        -- Commercial / Trade
                        'commercial_invoice',
                        'packing_list',
                        'certificate_of_origin',
                        'dangerous_goods_declaration',
                        'phytosanitary_certificate',
                        'veterinary_certificate',
                        -- Transport
                        'road_waybill',
                        'cmr_note',
                        'road_consignment_note',
                        'customs_road_manifest',
                        -- Customs
                        'sad_500',
                        'sad_502',
                        'sad_505',
                        'sad_507',
                        'export_declaration',
                        'import_declaration',
                        'transit_bond',
                        'srctd',
                        -- Permits & Licences
                        'cbrrta_permit',
                        'sadc_driver_certificate',
                        'prdp',
                        'import_permit',
                        'export_permit',
                        -- Insurance
                        'comesa_yellow_card',
                        'git_insurance',
                        'temporary_import_permit',
                        -- Driver's Pack docs
                        'vehicle_licence',
                        'drivers_licence',
                        'id_document',
                        'insurance_letter',
                        -- Other
                        'pod_photo',
                        'other'
                    )),
    filename        TEXT NOT NULL,
    storage_key     TEXT NOT NULL,                -- Key in SeaweedFS
    mime_type       TEXT,
    size_bytes      BIGINT,
    ocr_result      JSONB,                        -- OCR extraction results (Phase 3)
    ocr_confidence  NUMERIC(5,2),
    uploaded_by     UUID REFERENCES users(id),
    uploaded_via    TEXT DEFAULT 'web'
                    CHECK (uploaded_via IN ('web', 'whatsapp', 'api', 'sync')),
    -- Verification (HITL for billing-triggering docs)
    verified        BOOLEAN DEFAULT false,
    verified_by     UUID REFERENCES users(id),
    verified_at     TIMESTAMPTZ,
    verification_notes TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- DRIVER'S PACKS (KYC per driver or vehicle)
-- ============================================================
CREATE TABLE drivers_packs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    driver_id       UUID REFERENCES drivers(id),
    vehicle_id      UUID REFERENCES vehicles(id),
    -- At least one of driver_id or vehicle_id must be non-null
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending',
                        'auto_verified',
                        'flagged',
                        'manually_cleared',
                        'expired'
                    )),
    -- State tracking
    submitted_at    TIMESTAMPTZ,
    verified_at     TIMESTAMPTZ,
    flagged_at      TIMESTAMPTZ,
    cleared_at      TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,                  -- Scheduled re-validation
    -- Review
    reviewed_by     UUID REFERENCES users(id),
    review_notes    TEXT,
    -- Document references (denormalized for quick access)
    vehicle_licence_doc_id   UUID REFERENCES documents(id),
    drivers_licence_doc_id   UUID REFERENCES documents(id),
    id_document_doc_id       UUID REFERENCES documents(id),
    insurance_letter_doc_id  UUID REFERENCES documents(id),
    -- OCR cross-check
    ocr_cross_check JSONB,                        -- Consistency check results
    ocr_pass        BOOLEAN,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- SYNC EVENTS (Flutter outbox — append only)
-- ============================================================
CREATE TABLE sync_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    trip_id         UUID NOT NULL REFERENCES trips(id),
    event_uuid      UUID NOT NULL,                -- Client-generated UUID
    device_id       TEXT NOT NULL,
    event_type      TEXT NOT NULL
                    CHECK (event_type IN (
                        'status_update',
                        'pod_capture',
                        'border_doc_upload',
                        'location_ping',
                        'message_log',
                        'other'
                    )),
    payload         JSONB NOT NULL,
    idempotency_key TEXT GENERATED ALWAYS AS (event_uuid || ':' || device_id) STORED,
    processed       BOOLEAN DEFAULT false,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (event_uuid, device_id)
);

-- ============================================================
-- TRIP DOCUMENT CHECKLIST (required docs per trip)
-- ============================================================
CREATE TABLE trip_document_requirements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    trip_id         UUID NOT NULL REFERENCES trips(id),
    doc_type        TEXT NOT NULL,                 -- Same enum as documents.doc_type
    required        BOOLEAN DEFAULT true,          -- Is this doc mandatory for this trip?
    uploaded        BOOLEAN DEFAULT false,         -- Has a matching document been uploaded?
    document_id     UUID REFERENCES documents(id), -- FK to the uploaded document
    -- Route-aware: which country requires this doc
    required_by     TEXT,                          -- Country code (e.g., 'ZA', 'ZW', 'MZ')
    category        TEXT NOT NULL                  -- 'commercial', 'transport', 'customs', 'permit', 'insurance'
                    CHECK (category IN ('commercial', 'transport', 'customs', 'permit', 'insurance')),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trip_doc_req_trip ON trip_document_requirements(trip_id);
CREATE INDEX idx_trip_doc_req_unuploaded ON trip_document_requirements(trip_id, uploaded) WHERE uploaded = false;

-- ============================================================
-- NOTIFICATION LOG (audit trail)
-- ============================================================
CREATE TABLE notification_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),  -- NULL for platform-level
    channel         TEXT NOT NULL CHECK (channel IN ('whatsapp', 'sms', 'email', 'console')),
    recipient       TEXT NOT NULL,
    subject         TEXT,
    body            TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent', 'failed', 'rate_limited')),
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    sent_at         TIMESTAMPTZ
);
```

### 3.3 Indexes

```sql
-- Performance-critical indexes
CREATE INDEX idx_trips_tenant_status ON trips(tenant_id, status);
CREATE INDEX idx_trips_tracking_token ON trips(tracking_token) WHERE tracking_token IS NOT NULL;
CREATE INDEX idx_trips_carrier_token ON trips(carrier_token) WHERE carrier_token IS NOT NULL;
CREATE INDEX idx_invoices_tenant_status ON invoices(tenant_id, status);
CREATE INDEX idx_drivers_packs_tenant_status ON drivers_packs(tenant_id, status);
CREATE INDEX idx_sync_events_unprocessed ON sync_events(tenant_id, processed) WHERE processed = false;
CREATE INDEX idx_documents_trip ON documents(trip_id) WHERE trip_id IS NOT NULL;
CREATE INDEX idx_documents_pack ON documents(drivers_pack_id) WHERE drivers_pack_id IS NOT NULL;
CREATE INDEX idx_notification_log_pending ON notification_log(status, created_at) WHERE status = 'pending';
```

---

## 4. State Machines

### 4.1 Invoice Milestone State Machine

```
                    ┌─────────────┐
                    │   draft     │
                    └──────┬──────┘
                           │ issue_invoice()
                    ┌──────▼──────┐
                    │   issued    │
                    └──────┬──────┘
                           │ request_upfront()
                    ┌──────▼──────────┐
                    │upfront_requested │
                    └──────┬──────────┘
                           │ confirm_upfront_payment()
                    ┌──────▼──────────┐
                    │  upfront_paid   │
                    └──────┬──────────┘
                           │ begin_transit()
                    ┌──────▼──────────┐
                    │   in_transit    │
                    └──────┬──────────┘
                           │ capture_pod() (HITL)
                    ┌──────▼──────────┐
                    │  pod_captured   │
                    └──────┬──────────┘
                           │ verify_pod() (HITL — human confirms)
                    ┌──────▼──────────┐
                    │  pod_verified   │
                    └──────┬──────────┘
                           │ release_balance()
                    ┌──────▼──────────┐
                    │ balance_released│
                    └──────┬──────────┘
                           │ mark_fully_paid()
                    ┌──────▼──────────┐
                    │   fully_paid    │
                    └─────────────────┘
```

**Rules:**
- Transitions are **explicit function calls** on the state machine, never direct column updates.
- Each transition writes to `invoice_milestones` (append-only log).
- `pod_captured → pod_verified` is **HITL only** in Phase 1 — never auto-triggered.
- `upfront_amount` and `balance_amount` are computed at `issued` state and frozen.

### 4.2 Driver's Pack State Machine

```
              ┌─────────────┐
              │   pending    │
              └──────┬──────┘
                     │ ocr_auto_verify()
            ┌────────┴────────┐
            │                 │
     ┌──────▼──────┐  ┌──────▼──────┐
     │auto_verified│  │   flagged    │
     └──────┬──────┘  └──────┬──────┘
            │                │ admin_review()
            │         ┌──────▼───────────┐
            │         │manually_cleared  │
            │         └──────┬───────────┘
            │                │
            └───────┬────────┘
                    │  schedule_expiry()
              ┌─────▼─────┐
              │  expired   │
              └───────────┘
```

**Rules:**
- `pending → auto_verified | flagged`: Automatic Vision LLM extraction. If LLM fails, low confidence, or cross-document inconsistency → `flagged`.
- `flagged → manually_cleared`: Admin reviews in Tenant Admin KYC queue.
- Any state → `expired`: Scheduled Taskiq job checks `expires_at` and flags.
- **Hard gate:** Trip cannot reach `contract_awarded` if assigned driver/vehicle has `pending` or `expired` pack.

---

## 5. SADC Document Registry (Modular)

### 5.1 Structure

The document system lives in `app/core/documents/` with each category in its own module:

```
app/core/documents/
├── __init__.py        # Public API — re-exports registry functions
├── commercial.py      # Commercial/trade documents
├── transport.py       # Transport documents
├── customs.py         # Customs declarations
├── permits.py         # Permits & licences
├── insurance.py       # Insurance documents
├── driver_pack.py     # Driver's pack documents
└── registry.py        # Central registry, route-aware logic
```

### 5.2 DocType Dataclass

Every document type is defined as a `DocType` dataclass:

```python
@dataclass(frozen=True)
class DocType:
    key: str                    # Database value (e.g., "commercial_invoice")
    label: str                  # Human-readable name
    description: str            # Full regulatory context
    category: str               # "commercial", "transport", "customs", "permit", "insurance"
    mandatory: bool = True      # Default requirement status
    sacu_only: bool = False     # Simplified SACU-only documentation
    ocr_extractable: bool = False  # Phase 3 OCR flag
    transit_countries: list[str] | None = None  # Required only for specific transit routes
```

### 5.3 Route-Aware Requirements

```python
from app.core.documents import get_required_doc_types, is_sacu_only

# Full SADC route (30+ documents)
docs = get_required_doc_types("ZA", "ZW", ["MZ"])

# SACU-only route (simplified)
sacu_docs = get_required_doc_types("ZA", "BW")

# Check if route qualifies for SACU simplification
if is_sacu_only("ZA", "BW"):
    # Reduced documentation requirements
    ...
```

### 5.4 Category Modules

| Module | Document Types | Examples |
|--------|----------------|----------|
| `commercial.py` | 6 | Commercial Invoice, Packing List, Certificate of Origin, DG Declaration, Phytosanitary, Veterinary |
| `transport.py` | 4 | Road Waybill, CMR Note, Consignment Note, DA 187 Manifest |
| `customs.py` | 7 | SAD 500/502/505/507, Export/Import Declarations, Transit Bond, SRCTD |
| `permits.py` | 5 | CBRTA Permit, SADC Driver Certificate, PrDP, Import/Export Permits |
| `insurance.py` | 3 | COMESA Yellow Card, GIT Insurance, Temporary Import Permit |
| `driver_pack.py` | 4 | Vehicle Licence, Driver's Licence, ID Document, Insurance Letter |

### 5.5 Usage in Validation

```python
# Pre-departure document validation
async def validate_trip_documents(trip_id: UUID, db: AsyncSession):
    trip = await db.get(Trip, trip_id)
    required = get_required_doc_types(
        trip.origin_country,
        trip.destination_country,
        trip.transit_countries
    )
    uploaded = await get_uploaded_doc_types(trip_id, db)

    missing = [doc for doc in required if doc.key not in uploaded]
    if missing:
        raise DocumentValidationError(
            f"Missing required documents: {[d.label for d in missing]}"
        )
```

---

## 6. LLM Document Extraction (Vision LLM)

### 6.1 Architecture

No local OCR. Images are sent directly to vision-capable LLMs for structured data extraction.

```
Image Upload → PIL decode → Base64 encode → Vision LLM → Structured JSON
                                                              ↓
                                                    { doc_type, confidence, fields, summary }
                                                              ↓
                                                    Post-processing (expiry calc, normalization)
                                                              ↓
                                                    Validation (blacklist, format, cross-doc)
```

### 6.2 Multi-Provider Fallback

| Priority | Provider | Model | Cost/Page | Notes |
|----------|----------|-------|-----------|-------|
| 1 (Primary) | Mistral | ministral-14b-latest | ~$0.001 | Fast, good accuracy |
| 2 (Fallback) | Google Gemini | gemini-2.5-flash | ~$0.00075 | Cheapest, fast |
| 3 (Fallback) | OpenRouter | openai/gpt-4o-mini | ~$0.001 | Best accuracy |

**Automatic retry**: 3 attempts per provider with exponential backoff on 429/5xx errors.

### 6.3 Document Categories & Prompts

| Category | Prompt | Extracted Fields |
|----------|--------|------------------|
| **Driver's Pack** | `_prompt_driver_pack()` | Vehicle: reg, make_model, VIN, expiry. Driver: name, id_number, licence_code, valid_to. Insurance: insurer, cover_type, sum_insured |
| **Proof of Delivery** | `_prompt_pod()` | delivery_date, delivered_to, receiver_id, cargo_condition, damage_notes, signature_present |
| **Border Clearance** | `_prompt_border_clearance()` | permit_number, authorised_countries, declaration_number, covered_countries, valid_to |
| **General** | `_prompt_general()` | Auto-detect doc_type, extract all visible fields |

### 6.4 Configuration (env vars)

```env
LLM_ENABLED=true
LLM_PROVIDERS=mistral,google          # comma-separated priority order

MISTRAL_API_KEY=...                   # Primary provider
MISTRAL_VISION_MODEL=ministral-14b-latest

GOOGLE_API_KEY=...                    # Fallback
GOOGLE_VISION_MODEL=gemini-2.5-flash

OPENROUTER_API_KEY=...               # Optional fallback
OPENROUTER_VISION_MODEL=openai/gpt-4o-mini

LLM_MAX_CONCURRENT_PAGES=3           # Semaphore for batch processing
```

### 6.5 Usage

```python
from app.services.llm_extractor import get_extractor, post_process_result

extractor = get_extractor()

# Single image extraction
result = extractor.extract(image, doc_category="driver_pack")
result = post_process_result(result)
# result = { "doc_type": "VEHICLE_LICENCE", "confidence": 0.95, "fields": {...}, "summary": "🚛 Truck: CKG992X | Powerstar" }

# Async extraction
result = await extractor.extract_async(image, doc_category="pod")

# Batch extraction (Driver's Pack with multiple docs)
results = await extractor.extract_batch(
    images=[("vehicle", vehicle_img), ("licence", licence_img), ("insurance", insurance_img)],
    doc_category="driver_pack",
    max_concurrent=3,
)
```

### 6.6 Post-Processing

After LLM extraction, fields are normalized:
- Vehicle licence: expiry date → `is_expired`, `days_to_expiry`
- Insurance: string → boolean `is_legit`
- Plate normalization: uppercase, strip whitespace

### 6.7 Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| Primary provider 429 (rate limit) | Retry 2x with backoff, then try next provider |
| Primary provider 5xx (server error) | Retry 2x, then try next provider |
| All providers fail | Return `rejection_flag: "LLM_UNAVAILABLE"` |
| LLM returns invalid JSON | Return `rejection_flag: "LLM_PARSE_ERROR"` |
| Low confidence (< 0.5) | Admin review queue flag |

### 6.8 Source

Adapted from `reference_copy/apex_ai-bot/ocr/app/services/simple_llm_extractor.py` (v4 — Vision LLM only, no PaddleOCR).

---

## 7. Document Template System (Admin-Configurable)

### 7.1 Architecture

Document templates are **data-driven** — YAML files define fields, validation rules, and extraction prompts. Admins can add/tune templates via API without code changes.

```
document_templates/          # YAML templates (one per doc type)
        ↓
TemplateRegistry             # Loads YAML, provides lookup
        ↓
PromptBuilder                # Dynamic prompt from template
        ↓
LLM Extraction               # Sends prompt + image to LLM
        ↓
ResponseValidator            # Validates against template schema
        ↓
ExtractionResult             # Fields + validation + metadata
```

### 7.2 Template Structure

```yaml
# document_templates/vehicle_licence.yaml
doc_type: VEHICLE_LICENCE
category: driver_pack
label: Motor Vehicle Licence
version: 1
confidence_threshold: 0.7

fields:
  - name: reg_number
    type: string
    required: true
    pattern: "^[A-Z]{2,3}\\s?\\d{2,4}[\\s-]?\\w{0,3}$"
    description: "Licence plate (e.g., CKG992X)"
    examples: ["CKG992X", "MM17PX GP"]
    validation:
      - type: regex
        pattern: "^[A-Z]{2,3}\\s?\\d{2,4}$"
        message: "Invalid registration format"

  - name: expiry_date
    type: date
    required: true
    format: "YYYY-MM-DD"
    validation:
      - type: not_expired
        message: "Vehicle licence has expired"

visual_hints: |
  Look for: licence plate, make/model, VIN, expiry date.
```

### 7.3 Field Types

| Type | Description | Validation Options |
|------|-------------|-------------------|
| `string` | Text value | `pattern`, `allowed_values` |
| `number` | Numeric value | `range` (min/max) |
| `date` | Date value | `not_expired`, `format` |
| `boolean` | True/false | `equals` |
| `list` | Array of values | — |

### 7.4 Built-in Validation Rules

| Rule | Description | Fields |
|------|-------------|--------|
| `not_expired` | Date must be in future | date fields |
| `id_checksum` | SA ID 13-digit checksum | id_number |
| `range` | Numeric min/max | number fields |
| `equals` | Must equal value | boolean fields |
| `regex` | Pattern match | string fields |

### 7.5 Admin API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/templates` | List all templates |
| GET | `/api/v1/admin/templates/{doc_type}` | Get specific template |
| POST | `/api/v1/admin/templates` | Create new template |
| PUT | `/api/v1/admin/templates/{doc_type}` | Update template |
| DELETE | `/api/v1/admin/templates/{doc_type}` | Delete template |
| POST | `/api/v1/admin/templates/reload` | Reload from disk |
| POST | `/api/v1/admin/templates/test` | Test extraction with sample image |

### 7.6 Adding a New Document Type

1. Create YAML template in `document_templates/`:

```yaml
# document_templates/my_new_doc.yaml
doc_type: MY_NEW_DOC
category: border
label: My New Document
fields:
  - name: field1
    type: string
    required: true
    description: "Description of field1"
  - name: field2
    type: date
    required: false
    format: "YYYY-MM-DD"
visual_hints: |
  Look for: field1, field2 in the document.
```

2. Call `POST /api/v1/admin/templates/reload` or restart the service
3. The LLM extractor will now automatically use this template for extraction

### 7.7 Tuning Extraction

Admins can tune extraction by:

1. **Adding examples** — helps LLM understand expected format:
   ```yaml
   examples: ["CKG992X", "MM17PX GP"]
   ```

2. **Adding visual hints** — describes where to look in the document:
   ```yaml
   visual_hints: |
     The document is usually a rectangular card with the expiry date
     prominently displayed in the top-right corner.
   ```

3. **Adding custom prompt instructions** — extra context for the LLM:
   ```yaml
   custom_prompt_addition: |
     If the document is in Afrikaans, translate field values to English.
     If the image is blurry, return confidence < 0.5.
   ```

4. **Adjusting confidence threshold** — controls when to flag for review:
   ```yaml
   confidence_threshold: 0.8  # Higher = more strict
   ```

5. **Adding validation rules** — catches bad extractions:
   ```yaml
   validation:
     - type: not_expired
       message: "Document has expired"
     - type: range
       min: 1000
       max: 100000
       message: "Unusual value"
   ```

### 7.8 Template Files

```
app/document_templates/
├── vehicle_licence.yaml
├── drivers_licence.yaml
├── id_document.yaml
├── insurance_letter.yaml
├── pod_photo.yaml
├── pod_document.yaml
├── cross_border_permit.yaml
├── customs_declaration.yaml
├── comesa_yellow_card.yaml
├── transit_bond.yaml
└── certificate_of_origin.yaml
```

---

## 8. API Surface (v1)

### 6.1 Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/login` | None | Returns JWT access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Refresh token | Returns new access token |

### 6.2 Tenant-Scoped CRUD

All endpoints below require `Bearer` JWT and are automatically scoped to the user's `tenant_id` via RLS.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/carriers` | List/create carriers |
| GET/PUT/DELETE | `/api/v1/carriers/{id}` | Carrier detail |
| GET/POST | `/api/v1/drivers` | List/create drivers (under carrier) |
| GET/PUT/DELETE | `/api/v1/drivers/{id}` | Driver detail |
| GET/POST | `/api/v1/vehicles` | List/create vehicles (under carrier) |
| GET/PUT/DELETE | `/api/v1/vehicles/{id}` | Vehicle detail |

### 6.3 Trip Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/trips` | List/create trips |
| GET | `/api/v1/trips/{id}` | Trip detail with full state |
| PUT | `/api/v1/trips/{id}` | Update trip details |
| POST | `/api/v1/trips/{id}/send-quotation` | Send quotation to client |
| POST | `/api/v1/trips/{id}/award-contract` | Award contract (validates driver pack) |
| POST | `/api/v1/trips/{id}/assign` | Assign carrier/driver/vehicle |
| POST | `/api/v1/trips/{id}/begin-transit` | Mark in transit |
| POST | `/api/v1/trips/{id}/complete` | Mark delivered |
| POST | `/api/v1/trips/{id}/cancel` | Cancel trip |

### 6.4 Invoice & Milestones

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/invoices` | List invoices |
| GET | `/api/v1/invoices/{id}` | Invoice detail + milestone history |
| POST | `/api/v1/invoices/{id}/issue` | Issue invoice (computes 70/30 split) |
| POST | `/api/v1/invoices/{id}/request-upfront` | Trigger upfront payment request |
| POST | `/api/v1/invoices/{id}/confirm-upfront` | Confirm upfront payment received |
| POST | `/api/v1/invoices/{id}/verify-pod` | Human-verify PoD → unlock balance |
| POST | `/api/v1/invoices/{id}/release-balance` | Release 30% balance |
| GET | `/api/v1/invoices/{id}/milestones` | Full milestone event log |

### 6.5 Driver's Pack (KYC)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/drivers-packs` | List/create packs |
| GET | `/api/v1/drivers-packs/{id}` | Pack detail + document refs |
| POST | `/api/v1/drivers-packs/{id}/submit` | Submit for review |
| POST | `/api/v1/drivers-packs/{id}/clear` | Admin manual clearance |
| POST | `/api/v1/drivers-packs/{id}/flag` | Admin manual flag |
| GET | `/api/v1/drivers-packs/queue` | Admin review queue (flagged packs) |

### 6.6 Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload document (multipart) |
| GET | `/api/v1/documents/{id}` | Get document metadata |
| GET | `/api/v1/documents/{id}/download` | Pre-signed download URL |
| GET | `/api/v1/trips/{trip_id}/documents` | List documents for trip |
| GET | `/api/v1/drivers-packs/{pack_id}/documents` | List documents for pack |

### 6.7 Sync (Flutter Outbox)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sync/events` | Batch upload sync events |
| GET | `/api/v1/sync/events` | Poll for unprocessed events |

### 6.8 Public (No Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/track/{token}` | Public tracking link — milestone progress, doc vault |
| GET | `/track/{token}/status` | Polling endpoint — latest status (client auto-refresh) |
| GET | `/carrier/{token}` | Carrier portal — trip details, action forms |
| POST | `/carrier/{token}/accept` | Carrier accepts trip |
| POST | `/carrier/{token}/pod` | Carrier uploads PoD |
| POST | `/carrier/{token}/border-docs` | Carrier uploads border clearance docs |

---

## 7. Authentication & Authorization

### 6.1 JWT Structure

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "role": "tenant_admin",
  "exp": 1234567890,
  "iat": 1234567800
}
```

### 6.2 Role Hierarchy

| Role | Scope | Permissions |
|------|-------|-------------|
| `super_admin` | Platform-wide | All tenants, system config, backups |
| `tenant_admin` | Own tenant | Full CRUD, KYC review, invoice operations |
| `tenant_staff` | Own tenant | Trip/document CRUD, limited invoice ops |

### 6.3 Dependency Injection

```python
# deps.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode JWT, return User or raise 401."""
    ...

async def get_current_tenant(user: User = Depends(get_current_user)) -> Tenant:
    """Extract tenant from user, raise 403 if inactive."""
    ...

async def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Raise 403 if not super_admin."""
    ...
```

---

## 8. Task Queue (Taskiq + Redis)

### 7.1 Configuration

```python
# tasks/worker.py
from taskiq import TaskiqRedisBroker

broker = TaskiqRedisBroker(url="redis://localhost:6379")
```

### 7.2 Phase 1 Tasks

| Task | Trigger | Description |
|------|---------|-------------|
| `dispatch_notification` | On notification create | Async send via NotificationDispatcher |
| `revalidate_drivers_packs` | Daily cron | Check `expires_at`, flag expired packs |
| `process_sync_events` | On sync event batch | Validate, deduplicate, trigger state changes |
| `check_invoice_overdue` | Daily cron | Flag invoices past due date |

### 7.3 Task Pattern

```python
@broker.task
async def dispatch_notification(notification_id: UUID):
    """Send notification via appropriate channel."""
    async with get_db() as db:
        notification = await db.get(NotificationLog, notification_id)
        notifier = get_notifier(notification.channel)
        await notifier.send(notification)
```

---

## 9. Object Storage (SeaweedFS)

### 8.1 Storage Interface

```python
# storage/base.py
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store object, return storage key."""
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve object by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object by key."""
        ...

    @abstractmethod
    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate pre-signed download URL."""
        ...
```

### 8.2 Key Naming Convention

```
{tenant_id}/{doc_type}/{trip_or_pack_id}/{uuid}_{filename}
```

Example: `a1b2c3d4/pod_photo/trip-uuid/abc123_image.jpg`

---

## 10. NotificationDispatcher Interface

```python
# notifications/base.py
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> bool:
        """Send notification. Returns True if sent, False if failed."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if channel is available (rate limits, API status)."""
        ...
```

### 9.1 Phase 1 Adapters

| Adapter | Status | Notes |
|---------|--------|-------|
| `ConsoleNotifier` | **Active** | Logs to stdout — default for dev |
| `WhatsAppNotifier` | **Stub** | Meta Cloud API — Phase 2, interface ready |
| `SMSNotifier` | **Stub** | Placeholder for future |
| `EmailNotifier` | **Stub** | Placeholder for future |

### 9.2 WhatsApp Down Scenario

If WhatsApp is unavailable (Phase 1 reality):
- All notifications log to `notification_log` with `status = 'rate_limited'` or `status = 'failed'`.
- Tracking links (`/track/{token}`) remain fully functional — no WhatsApp dependency.
- Carrier portal (`/carrier/{token}`) remains fully functional.
- Admin sees notification failures in audit log and can retry or use alternative channel.

---

## 11. Tokenized Links

### 10.1 Token Generation

```python
# core/token.py
import secrets

def generate_tracking_token() -> str:
    """Generate URL-safe token for tracking links."""
    return secrets.token_urlsafe(32)

def generate_carrier_token() -> str:
    """Generate URL-safe token for carrier portal."""
    return secrets.token_urlsafe(32)
```

### 10.2 Token Scoping

- **Tracking token:** Read-only access to trip milestones, client-visible documents, live location.
- **Carrier token:** Read + write access to accept trip, upload PoD, upload border docs.
- Tokens are **single-use per action** where write is involved (accept, upload).
- Tokens are stored on the `trips` table and validated on each request.

### 10.3 Public Endpoint Auth

```python
# api/public/tracking.py
router = APIRouter()

@router.get("/track/{token}")
async def get_tracking(token: str, db: AsyncSession = Depends(get_db)):
    trip = await db.execute(
        select(Trip).where(Trip.tracking_token == token)
    )
    if not trip:
        raise HTTPException(404, "Invalid tracking link")
    return build_tracking_response(trip)
```

---

## 12. Development Setup (Docker Desktop)

### 11.1 Prerequisites

- Docker Desktop (Windows/Mac/Linux)
- Python 3.12+ (for local IDE/tooling only — app runs in Docker)

### 11.2 Quick Start — Full Docker Stack

```bash
cd backend

# 1. Copy environment file
cp .env.example .env

# 2. Build and start everything
docker compose up -d --build

# 3. Run migrations (inside running container)
docker compose exec backend alembic upgrade head

# 4. Seed super admin
docker compose exec backend python -m app.scripts.seed_admin

# 5. Verify
curl http://localhost:8000/health
```

**All backend services run inside Docker — no local Python setup required for the app itself.**

### 11.3 Services (Docker Desktop)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `backend` | df-backend | 8000 | FastAPI API server |
| `taskiq-worker` | df-taskiq | — | Background task worker |
| `postgres` | df-postgres | 5432 | PostgreSQL 16 |
| `redis` | df-redis | 6379 | Queue + cache |
| `seaweed-master` | df-seaweed-master | 9333 | SeaweedFS master |
| `seaweed-volume` | df-seaweed-volume | 8080 | SeaweedFS volume |
| `seaweed-s3` | df-seaweed-s3 | 8333 | S3-compatible API |

### 11.4 Common Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f taskiq-worker

# Restart a service
docker compose restart backend

# Stop everything
docker compose down

# Stop and wipe data (fresh start)
docker compose down -v

# Rebuild after code changes
docker compose up -d --build

# Run alembic migration
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Shell into backend container
docker compose exec backend bash

# Run tests (from host)
docker compose exec backend pytest
```

### 11.5 Local Development (Optional — Hot Reload)

For faster iteration, run the API locally with hot reload while infra stays in Docker:

```bash
# Start only infrastructure
docker compose up -d postgres redis seaweed-master seaweed-volume seaweed-s3

# Run locally with hot reload
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 11.6 docker-compose.yml

See [docker-compose.yml](./docker-compose.yml) — includes health checks, dependency ordering, and named volumes.

---

## 13. Testing Strategy

### 12.1 Test Types

| Type | Framework | Coverage Target |
|------|-----------|-----------------|
| Unit | pytest | State machines, token gen, currency validation |
| Integration | pytest-asyncio + testcontainers | DB queries, RLS isolation, API endpoints |
| E2E | httpx + test DB | Full request cycle for critical paths |

### 12.2 Key Test Scenarios

1. **RLS isolation:** User from Tenant A cannot read/write Tenant B data.
2. **Invoice state machine:** All valid transitions succeed; invalid transitions raise.
3. **Driver's Pack gate:** Trip cannot be awarded if pack is pending/expired.
4. **Tokenized links:** Valid token returns data; invalid/tampered token returns 404.
5. **Sync idempotency:** Duplicate `(event_uuid, device_id)` is rejected.
6. **Notification fallback:** WhatsApp unavailable → notification logged as failed, no crash.

### 12.3 Running Tests

```bash
pytest                          # All tests
pytest -m "not integration"     # Unit only
pytest -m integration           # Integration only
pytest --cov=app --cov-report=html  # Coverage
```

---

## 14. Linting & Type Checking

```bash
ruff check .                    # Linting
ruff format .                   # Formatting
mypy .                          # Type checking
pyright                         # Strict type checking
```

---

## 15. Deployment (Phase 1)

### 14.1 Single-VM Topology

```
┌─────────────────────────────────────────┐
│              Single VM                  │
│                                         │
│  ┌─────────┐  ┌──────────────────────┐  │
│  │  Caddy   │──│  FastAPI (uvicorn)   │  │
│  │  :443    │  │  :8000               │  │
│  │  :80     │  └──────────────────────┘  │
│  └─────────┘                            │
│       │       ┌──────────────────────┐  │
│       │       │  Taskiq Worker       │  │
│       │       │  (background tasks)  │  │
│       │       └──────────────────────┘  │
│       │                                 │
│  ┌────▼────────────────────────────┐   │
│  │  Docker Compose                 │   │
│  │  ┌──────────┐ ┌─────┐ ┌──────┐ │   │
│  │  │PostgreSQL│ │Redis│ │Seawee│ │   │
│  │  │  :5432   │ │:6379│ │ :8333│ │   │
│  │  └──────────┘ └─────┘ └──────┘ │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 14.2 Caddyfile

```
deliveryflow.yourdomain.com {
    reverse_proxy localhost:8000

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }

    encode gzip
}
```

### 14.3 Backups

- Nightly `pg_dump` → compressed → SeaweedFS → off-site sync
- SeaweedFS snapshots weekly
- Restore procedure documented in DEVOPS_PLAN.md

---

## 16. Tracking Updates — Polling Model (Phase 1)

Phase 1 uses **HTTP polling** for tracking updates — no WebSocket. This keeps the stack simple and lets us integrate third-party car trackers (GPS providers) via their own webhooks/APIs later.

### 15.1 Polling Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /track/{token}/status` | None (public) | Returns latest trip status + milestone progress |
| `GET /api/v1/trips/{id}/status` | JWT | Returns trip status (tenant-scoped) |

### 15.2 Polling Strategy for Clients

- Client-side auto-refresh every **30 seconds** (configurable).
- Response includes `last_updated` timestamp — client skips re-render if unchanged.
- Admin dashboard polls every **10 seconds** for active trips.
- Tracking link page polls every **15 seconds**.

### 15.3 Future Tracking Integration

Third-party car tracker data flows in via:
1. Webhook from tracker provider → `POST /api/v1/trips/{id}/location` (Phase 2+)
2. Stored in `trip.location_data` JSONB column
3. Polled by client via existing status endpoint

No WebSocket needed — the tracker provider handles their own real-time layer.

---

## 17. Open Items for Backend

- [ ] Pagination strategy (cursor vs offset) — finalize during API implementation.
- [ ] Rate limiting per tenant — Caddy or FastAPI middleware decision.
- [ ] Document versioning — Phase 1 stores latest only; versioning deferred.
- [ ] Audit logging for all mutations — implement via SQLAlchemy event listeners.
- [ ] Third-party car tracker webhook format — define schema when provider selected.

---

*This plan is the source of truth for backend implementation. Reference [MASTER_PLAN.md](../MASTER_PLAN.md) for shared domain decisions.*
