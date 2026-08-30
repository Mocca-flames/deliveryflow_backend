from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.deps import get_current_tenant, get_current_user, get_db
from app.main import app


@pytest.fixture
def override_auth():
    tenant = SimpleNamespace(id=uuid4(), name="Test Tenant")
    user = SimpleNamespace(id=uuid4(), role="tenant_admin", is_active=True, tenant=tenant)

    async def fake_db():
        yield None

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_tenant] = lambda: tenant
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_document_template_list_and_create(override_auth):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/document-templates")
        assert res.status_code == 200

        payload = {
            "name": "Client Quotation",
            "document_type": "quotation",
            "category": "client",
            "description": "Default quotation template",
            "data": {
                "client_name": "Acme Ltd",
                "currency": "ZAR",
                "notes": "Standard terms",
            },
        }
        create = await client.post("/api/v1/document-templates", json=payload)
        assert create.status_code == 201
        body = create.json()
        assert body["name"] == "Client Quotation"
        assert body["document_type"] == "quotation"


@pytest.mark.asyncio
async def test_document_generate_endpoint(override_auth):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "document_type": "quotation",
            "client_name": "Acme Ltd",
            "client_email": "billing@acme.co",
            "currency": "ZAR",
            "reference": "Q-1001",
            "validity_days": 30,
            "items": [{
                "description": "Freight",
                "quantity": 1,
                "unit": "trip",
                "unit_price": 2000,
                "tax_rate": 15,
                "total": 2300,
            }],
            "notes": "Standard terms",
            "payment_terms": "Net 30",
        }
        res = await client.post("/api/v1/documents/generate", json=payload)
        assert res.status_code == 200
        assert res.json()["document_type"] == "quotation"

        pdf_res = await client.post("/api/v1/documents/generate/quotation/pdf", json=payload)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"].startswith("application/pdf")
