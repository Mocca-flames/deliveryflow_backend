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
│   │   └── currency.py          # Currency code validation (ZAR default, no logic yet)
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
│   │   ├── drivers_pack.py      # KYC orchestration, OCR trigger, review queue
│   │   ├── notification.py      # NotificationDispatcher interface
│   │   ├── sync.py              # Outbox sync processing
│   │   └── tracking.py          # Tokenized tracking link data
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
-- DOCUMENTS (uploaded files)
-- ============================================================
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    trip_id         UUID REFERENCES trips(id),
    drivers_pack_id UUID REFERENCES drivers_packs(id),
    doc_type        TEXT NOT NULL
                    CHECK (doc_type IN (
                        'contract',
                        'quotation',
                        'pod_photo',
                        'border_doc',
                        'vehicle_licence',
                        'drivers_licence',
                        'id_document',
                        'insurance_letter',
                        'other'
                    )),
    filename        TEXT NOT NULL,
    storage_key     TEXT NOT NULL,                -- Key in SeaweedFS
    mime_type       TEXT,
    size_bytes      BIGINT,
    ocr_result      JSONB,                        -- OCR extraction results
    ocr_confidence  NUMERIC(5,2),
    uploaded_by     UUID REFERENCES users(id),
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
- `pending → auto_verified | flagged`: Automatic OCR check. If OCR fails or cross-document inconsistency → `flagged`.
- `flagged → manually_cleared`: Admin reviews in Tenant Admin KYC queue.
- Any state → `expired`: Scheduled Taskiq job checks `expires_at` and flags.
- **Hard gate:** Trip cannot reach `contract_awarded` if assigned driver/vehicle has `pending` or `expired` pack.

---

## 5. API Surface (v1)

### 5.1 Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/login` | None | Returns JWT access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Refresh token | Returns new access token |

### 5.2 Tenant-Scoped CRUD

All endpoints below require `Bearer` JWT and are automatically scoped to the user's `tenant_id` via RLS.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/carriers` | List/create carriers |
| GET/PUT/DELETE | `/api/v1/carriers/{id}` | Carrier detail |
| GET/POST | `/api/v1/drivers` | List/create drivers (under carrier) |
| GET/PUT/DELETE | `/api/v1/drivers/{id}` | Driver detail |
| GET/POST | `/api/v1/vehicles` | List/create vehicles (under carrier) |
| GET/PUT/DELETE | `/api/v1/vehicles/{id}` | Vehicle detail |

### 5.3 Trip Lifecycle

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

### 5.4 Invoice & Milestones

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

### 5.5 Driver's Pack (KYC)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/drivers-packs` | List/create packs |
| GET | `/api/v1/drivers-packs/{id}` | Pack detail + document refs |
| POST | `/api/v1/drivers-packs/{id}/submit` | Submit for review |
| POST | `/api/v1/drivers-packs/{id}/clear` | Admin manual clearance |
| POST | `/api/v1/drivers-packs/{id}/flag` | Admin manual flag |
| GET | `/api/v1/drivers-packs/queue` | Admin review queue (flagged packs) |

### 5.6 Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload document (multipart) |
| GET | `/api/v1/documents/{id}` | Get document metadata |
| GET | `/api/v1/documents/{id}/download` | Pre-signed download URL |
| GET | `/api/v1/trips/{trip_id}/documents` | List documents for trip |
| GET | `/api/v1/drivers-packs/{pack_id}/documents` | List documents for pack |

### 5.7 Sync (Flutter Outbox)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sync/events` | Batch upload sync events |
| GET | `/api/v1/sync/events` | Poll for unprocessed events |

### 5.8 Public (No Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/track/{token}` | Public tracking link — milestone progress, doc vault |
| GET | `/track/{token}/status` | Polling endpoint — latest status (client auto-refresh) |
| GET | `/carrier/{token}` | Carrier portal — trip details, action forms |
| POST | `/carrier/{token}/accept` | Carrier accepts trip |
| POST | `/carrier/{token}/pod` | Carrier uploads PoD |
| POST | `/carrier/{token}/border-docs` | Carrier uploads border clearance docs |

---

## 6. Authentication & Authorization

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

## 7. Task Queue (Taskiq + Redis)

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

## 8. Object Storage (SeaweedFS)

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

## 9. NotificationDispatcher Interface

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

## 10. Tokenized Links

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

## 11. Development Setup (Docker Desktop)

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

## 12. Testing Strategy

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

## 13. Linting & Type Checking

```bash
ruff check .                    # Linting
ruff format .                   # Formatting
mypy .                          # Type checking
pyright                         # Strict type checking
```

---

## 14. Deployment (Phase 1)

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

## 15. Tracking Updates — Polling Model (Phase 1)

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

## 16. Open Items for Backend

- [ ] Pagination strategy (cursor vs offset) — finalize during API implementation.
- [ ] Rate limiting per tenant — Caddy or FastAPI middleware decision.
- [ ] Document versioning — Phase 1 stores latest only; versioning deferred.
- [ ] Audit logging for all mutations — implement via SQLAlchemy event listeners.
- [ ] Third-party car tracker webhook format — define schema when provider selected.

---

*This plan is the source of truth for backend implementation. Reference [MASTER_PLAN.md](../MASTER_PLAN.md) for shared domain decisions.*
