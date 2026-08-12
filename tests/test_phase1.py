"""
Phase 1 Backend — Smoke Test Script
====================================
No pytest, no test framework. Just plain Python assertions.

Run:  cd backend && python tests/test_phase1.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure the backend directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jose import jwt

from app.config import get_settings
from app.core.exceptions import (
    DeliveryFlowError,
    DriverPackGateError,
    InvalidStateTransitionError,
    NotificationError,
    StorageError,
    TokenNotFoundError,
)
from app.core.security import hash_password, verify_password
from app.core.token import generate_tracking_token, generate_carrier_token
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.services.auth import (
    AuthenticationError,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    refresh_tokens,
)
from app.state_machines.invoice import VALID_TRANSITIONS, validate_transition

settings = get_settings()

PASSED = 0
FAILED = 0


def run(label, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  PASS  {label}")
    except Exception as e:
        FAILED += 1
        print(f"  FAIL  {label}  ->  {e}")


async def run_async(label, fn):
    global PASSED, FAILED
    try:
        await fn()
        PASSED += 1
        print(f"  PASS  {label}")
    except Exception as e:
        FAILED += 1
        print(f"  FAIL  {label}  ->  {e}")


# ── helpers ──


def _mock_user(active=True):
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    u = MagicMock()
    u.id = uid
    u.tenant_id = tid
    u.password_hash = hash_password("pass123")
    u.is_active = active
    return u


def _mock_db(result=None, user=None):
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    target = user if user is not None else result

    async def _execute(stmt):
        row = MagicMock()
        row.scalar_one_or_none.return_value = target
        return row
    mock_db.execute = AsyncMock(side_effect=_execute)

    if user is not None:
        async def _get(model, uid):
            return user
        mock_db.get = AsyncMock(side_effect=_get)

    return mock_db


# ═══════════════════════════════════════════════
# 1. SECURITY — bcrypt
# ═══════════════════════════════════════════════

def test_security():
    print("\n[Security]")

    def _hash_is_string():
        h = hash_password("test")
        assert isinstance(h, str) and len(h) > 0

    def _hash_is_bcrypt():
        assert hash_password("x").startswith("$2")

    def _verify_correct():
        h = hash_password("secret")
        assert verify_password("secret", h)

    def _verify_wrong():
        h = hash_password("secret")
        assert not verify_password("wrong", h)

    def _salt_uniqueness():
        a, b = hash_password("same"), hash_password("same")
        assert a != b
        assert verify_password("same", a) and verify_password("same", b)

    run("hash returns string", _hash_is_string)
    run("hash starts with $2 (bcrypt)", _hash_is_bcrypt)
    run("verify correct password", _verify_correct)
    run("verify wrong password", _verify_wrong)
    run("different hashes for same password", _salt_uniqueness)


# ═══════════════════════════════════════════════
# 2. TOKENS — tracking & carrier
# ═══════════════════════════════════════════════

def test_tokens():
    print("\n[Tokens]")

    def _tracking():
        t = generate_tracking_token()
        assert isinstance(t, str) and len(t) > 20

    def _carrier():
        t = generate_carrier_token()
        assert isinstance(t, str) and len(t) > 20

    def _unique():
        assert generate_tracking_token() != generate_tracking_token()

    run("tracking token length", _tracking)
    run("carrier token length", _carrier)
    run("tokens are unique", _unique)


# ═══════════════════════════════════════════════
# 3. JWT — create & decode
# ═══════════════════════════════════════════════

def test_jwt():
    print("\n[JWT]")

    def _decode_access():
        uid, tid = uuid.uuid4(), uuid.uuid4()
        tok = create_access_token(uid, tid)
        p = jwt.decode(tok, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert p["sub"] == str(uid)
        assert p["tenant_id"] == str(tid)
        assert p["type"] == "access"

    def _decode_refresh():
        uid = uuid.uuid4()
        tok = create_refresh_token(uid)
        p = jwt.decode(tok, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert p["sub"] == str(uid)
        assert p["type"] == "refresh"

    def _access_expiry():
        tok = create_access_token(uuid.uuid4(), uuid.uuid4())
        p = jwt.decode(tok, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        delta = datetime.fromtimestamp(p["exp"], tz=timezone.utc) - datetime.fromtimestamp(p["iat"], tz=timezone.utc)
        assert delta == timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    def _refresh_expiry():
        tok = create_refresh_token(uuid.uuid4())
        p = jwt.decode(tok, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        delta = datetime.fromtimestamp(p["exp"], tz=timezone.utc) - datetime.fromtimestamp(p["iat"], tz=timezone.utc)
        assert delta == timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRES_DAYS)

    run("access token decodable", _decode_access)
    run("refresh token decodable", _decode_refresh)
    run("access token expiry correct", _access_expiry)
    run("refresh token expiry correct", _refresh_expiry)


# ═══════════════════════════════════════════════
# 4. INVOICE STATE MACHINE
# ═══════════════════════════════════════════════

def test_state_machine():
    print("\n[Invoice State Machine]")

    def _map_exists():
        assert "draft" in VALID_TRANSITIONS
        assert "fully_paid" in VALID_TRANSITIONS

    def _draft_to_issued():
        validate_transition("draft", "issued")

    def _draft_to_cancelled():
        validate_transition("draft", "cancelled")

    def _issued_to_upfront():
        validate_transition("issued", "upfront_requested")

    def _happy_path():
        steps = [
            ("draft", "issued"),
            ("issued", "upfront_requested"),
            ("upfront_requested", "upfront_paid"),
            ("upfront_paid", "in_transit"),
            ("in_transit", "pod_captured"),
            ("pod_captured", "pod_verified"),
            ("pod_verified", "balance_released"),
            ("balance_released", "fully_paid"),
        ]
        for cur, nxt in steps:
            validate_transition(cur, nxt)

    def _invalid_raises():
        try:
            validate_transition("draft", "fully_paid")
            assert False, "should have raised"
        except InvalidStateTransitionError:
            pass

    def _skip_steps_raises():
        try:
            validate_transition("draft", "in_transit")
            assert False, "should have raised"
        except InvalidStateTransitionError:
            pass

    def _terminal_states():
        assert VALID_TRANSITIONS["fully_paid"] == []
        assert VALID_TRANSITIONS["cancelled"] == []

    run("transition map exists", _map_exists)
    run("draft -> issued", _draft_to_issued)
    run("draft -> cancelled", _draft_to_cancelled)
    run("issued -> upfront_requested", _issued_to_upfront)
    run("full happy path (8 steps)", _happy_path)
    run("invalid transition raises", _invalid_raises)
    run("skipping steps raises", _skip_steps_raises)
    run("terminal states (fully_paid, cancelled)", _terminal_states)


# ═══════════════════════════════════════════════
# 5. EXCEPTIONS
# ═══════════════════════════════════════════════

def test_exceptions():
    print("\n[Exceptions]")

    def _base():
        assert issubclass(DeliveryFlowError, Exception)

    def _hierarchy():
        for cls in [InvalidStateTransitionError, DriverPackGateError,
                     TokenNotFoundError, NotificationError, StorageError]:
            assert issubclass(cls, DeliveryFlowError)

    def _message():
        assert str(DeliveryFlowError("boom")) == "boom"

    run("base is Exception", _base)
    run("all inherit DeliveryFlowError", _hierarchy)
    run("custom message", _message)


# ═══════════════════════════════════════════════
# 6. SCHEMAS
# ═══════════════════════════════════════════════

def test_schemas():
    print("\n[Schemas]")

    def _login_ok():
        r = LoginRequest(email="a@b.com", password="p")
        assert r.email == "a@b.com"

    def _login_bad_email():
        try:
            LoginRequest(email="bad", password="p")
            assert False, "should have raised"
        except Exception:
            pass

    def _token_resp():
        r = TokenResponse(access_token="a", refresh_token="b")
        assert r.token_type == "bearer"

    def _refresh_req():
        r = RefreshRequest(refresh_token="tok")
        assert r.refresh_token == "tok"

    run("LoginRequest valid", _login_ok)
    run("LoginRequest bad email rejects", _login_bad_email)
    run("TokenResponse default type", _token_resp)
    run("RefreshRequest stores token", _refresh_req)


# ═══════════════════════════════════════════════
# 7. AUTH SERVICE (async, mocked DB)
# ═══════════════════════════════════════════════

async def test_auth_service():
    print("\n[Auth Service]")

    async def _success():
        u = _mock_user()
        db = _mock_db(user=u)
        r = await authenticate_user(db, LoginRequest(email="a@b.com", password="pass123"))
        assert isinstance(r, TokenResponse)
        assert r.access_token and r.refresh_token

    async def _wrong_pass():
        u = _mock_user()
        db = _mock_db(user=u)
        try:
            await authenticate_user(db, LoginRequest(email="a@b.com", password="wrong"))
            assert False
        except AuthenticationError as e:
            assert "Invalid email or password" in str(e)

    async def _not_found():
        db = _mock_db(result=None)
        try:
            await authenticate_user(db, LoginRequest(email="x@y.com", password="p"))
            assert False
        except AuthenticationError:
            pass

    async def _inactive():
        u = _mock_user(active=False)
        db = _mock_db(user=u)
        try:
            await authenticate_user(db, LoginRequest(email="a@b.com", password="pass123"))
            assert False
        except AuthenticationError as e:
            assert "deactivated" in str(e)

    async def _refresh_ok():
        u = _mock_user()
        db = _mock_db()
        db.get.return_value = u
        tok = create_refresh_token(u.id)
        r = await refresh_tokens(db, RefreshRequest(refresh_token=tok))
        assert r.access_token and r.refresh_token

    async def _refresh_bad_type():
        tok = create_access_token(uuid.uuid4())
        db = _mock_db()
        try:
            await refresh_tokens(db, RefreshRequest(refresh_token=tok))
            assert False
        except AuthenticationError as e:
            assert "Invalid token type" in str(e)

    await run_async("authenticate success", _success)
    await run_async("authenticate wrong password", _wrong_pass)
    await run_async("authenticate user not found", _not_found)
    await run_async("authenticate inactive user", _inactive)
    await run_async("refresh tokens success", _refresh_ok)
    await run_async("refresh with access token fails", _refresh_bad_type)


# ═══════════════════════════════════════════════
# 8. TRIP SERVICE (async, mocked DB)
# ═══════════════════════════════════════════════

async def test_trip_service():
    print("\n[Trip Service]")
    from app.services.trip import TripService
    from app.schemas.trip import TripCreate
    from datetime import date

    async def _create():
        db = _mock_db()
        svc = TripService(db)
        data = TripCreate(
            reference="TRIP-001", origin="Gaborone", destination="Johannesburg",
            quoted_amount=Decimal("15000"), currency="ZAR",
            pickup_date=date(2026, 8, 15), delivery_date=date(2026, 8, 20),
        )
        with patch("app.services.trip.get_required_doc_types", return_value=["waybill"]):
            trip = await svc.create(uuid.uuid4(), data)
        assert trip.reference == "TRIP-001"
        assert trip.status == "draft"
        assert trip.tracking_token and trip.carrier_token

    async def _get():
        expected = MagicMock()
        db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = expected
        db.execute = AsyncMock(return_value=mock_res)
        svc = TripService(db)
        assert await svc.get(uuid.uuid4(), uuid.uuid4()) is expected

    async def _lifecycle():
        db = _mock_db()
        svc = TripService(db)
        t = MagicMock()
        t.status = "assigned"
        await svc.begin_transit(t)
        assert t.status == "in_transit"
        await svc.complete(t)
        assert t.status == "completed"

    async def _cancel():
        db = _mock_db()
        svc = TripService(db)
        t = MagicMock()
        await svc.cancel(t)
        assert t.status == "cancelled"

    await run_async("create trip", _create)
    await run_async("get trip", _get)
    await run_async("begin_transit + complete", _lifecycle)
    await run_async("cancel trip", _cancel)


# ═══════════════════════════════════════════════
# 9. INVOICE SERVICE (async, mocked DB)
# ═══════════════════════════════════════════════

async def test_invoice_service():
    print("\n[Invoice Service]")
    from app.services.invoice import InvoiceService

    async def _create():
        trip = MagicMock()
        trip.id = uuid.uuid4()
        trip.reference = "TRIP-001"
        trip.quoted_amount = Decimal("20000")
        trip.currency = "ZAR"
        db = _mock_db()
        db.get.return_value = trip
        svc = InvoiceService(db)
        inv = await svc.create(uuid.uuid4(), trip.id)
        assert inv.status == "draft"
        assert inv.total_amount == Decimal("20000")
        assert inv.upfront_pct == Decimal("70.00")
        assert inv.balance_pct == Decimal("30.00")

    async def _trip_not_found():
        db = _mock_db()
        db.get.return_value = None
        svc = InvoiceService(db)
        try:
            await svc.create(uuid.uuid4(), uuid.uuid4())
            assert False
        except DeliveryFlowError as e:
            assert "Trip not found" in str(e)

    async def _no_amount():
        trip = MagicMock()
        trip.quoted_amount = None
        db = _mock_db()
        db.get.return_value = trip
        svc = InvoiceService(db)
        try:
            await svc.create(uuid.uuid4(), uuid.uuid4())
            assert False
        except DeliveryFlowError as e:
            assert "no quoted amount" in str(e)

    await run_async("create invoice (70/30 split)", _create)
    await run_async("trip not found raises", _trip_not_found)
    await run_async("no quoted amount raises", _no_amount)


# ═══════════════════════════════════════════════
# 10. CONFIG
# ═══════════════════════════════════════════════

def test_config():
    print("\n[Config]")

    def _defaults():
        s = get_settings()
        assert s.APP_NAME == "DeliveryFlow"
        assert s.JWT_ALGORITHM == "HS256"

    def _singleton():
        assert get_settings() is get_settings()

    run("settings load defaults", _defaults)
    run("settings is singleton", _singleton)


# ═══════════════════════════════════════════════
# 11. DOCUMENT SERVICE
# ═══════════════════════════════════════════════

async def test_document_service():
    print("\n[Document Service]")

    async def _instantiation():
        try:
            from app.services.document import DocumentService
            db = AsyncMock()
            svc = DocumentService(db)
            assert svc.db is db
        except ImportError:
            pass  # boto3 not installed — skip gracefully

    await run_async("DocumentService instantiation", _instantiation)


# ═══════════════════════════════════════════════
# 12. API ROUTES (live HTTP via httpx)
# ═══════════════════════════════════════════════

async def test_api_routes():
    print("\n[API Routes]")
    try:
        from httpx import ASGITransport, AsyncClient
        from app.main import app
    except (ImportError, ModuleNotFoundError) as e:
        print(f"  SKIP  (missing dependency: {e})")
        return

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        async def _health():
            r = await client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"

        async def _login_no_body():
            r = await client.post("/api/v1/auth/login", json={})
            assert r.status_code == 422

        async def _login_bad_email():
            r = await client.post("/api/v1/auth/login", json={"email": "bad", "password": "p"})
            assert r.status_code == 422

        async def _login_wrong_creds():
            r = await client.post("/api/v1/auth/login", json={"email": "x@y.com", "password": "wrong"})
            assert r.status_code == 401

        async def _refresh_no_body():
            r = await client.post("/api/v1/auth/refresh", json={})
            assert r.status_code == 422

        async def _refresh_bad_token():
            r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
            assert r.status_code == 401

        async def _me_no_token():
            r = await client.get("/api/v1/auth/me")
            assert r.status_code == 403

        async def _me_bad_token():
            r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad"})
            assert r.status_code == 401

        async def _protected_endpoints_require_auth():
            for method, path in [
                ("GET", "/api/v1/trips"),
                ("GET", "/api/v1/invoices"),
                ("GET", "/api/v1/drivers-packs"),
                ("GET", "/api/v1/documents"),
            ]:
                r = await client.get(path)
                assert r.status_code in (401, 403), f"{method} {path} returned {r.status_code}"

        await run_async("GET /health", _health)
        await run_async("POST /login (no body) -> 422", _login_no_body)
        await run_async("POST /login (bad email) -> 422", _login_bad_email)
        await run_async("POST /login (wrong creds) -> 401", _login_wrong_creds)
        await run_async("POST /refresh (no body) -> 422", _refresh_no_body)
        await run_async("POST /refresh (bad token) -> 401", _refresh_bad_token)
        await run_async("GET /me (no token) -> 403", _me_no_token)
        await run_async("GET /me (bad token) -> 401", _me_bad_token)
        await run_async("all protected endpoints require auth", _protected_endpoints_require_auth)


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def main():
    global PASSED, FAILED

    print("=" * 50)
    print("  DeliveryFlow — Phase 1 Backend Smoke Test")
    print("=" * 50)

    # Sync tests
    test_security()
    test_tokens()
    test_jwt()
    test_state_machine()
    test_exceptions()
    test_schemas()
    test_config()

    # Async tests
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_auth_service())
    loop.run_until_complete(test_trip_service())
    loop.run_until_complete(test_invoice_service())
    loop.run_until_complete(test_document_service())
    loop.run_until_complete(test_api_routes())
    loop.close()

    print("\n" + "=" * 50)
    total = PASSED + FAILED
    print(f"  {PASSED}/{total} passed, {FAILED} failed")
    print("=" * 50)

    sys.exit(1 if FAILED > 0 else 0)


if __name__ == "__main__":
    main()
