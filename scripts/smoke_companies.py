"""Small executable smoke check for the company API.

Run with the backend available and optionally set DELIVERYFLOW_TOKEN to exercise
the authenticated collection endpoint as well.
"""
import asyncio
import os

import httpx


async def main() -> None:
    base_url = os.getenv("DELIVERYFLOW_API_URL", "http://localhost:8000")
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        health = await client.get("/health")
        health.raise_for_status()

        schema = await client.get("/openapi.json")
        schema.raise_for_status()
        paths = schema.json()["paths"]
        expected = {"/api/v1/companies/", "/api/v1/companies/{company_id}"}
        missing = expected - paths.keys()
        if missing:
            raise AssertionError(f"Company routes missing from OpenAPI: {sorted(missing)}")

        token = os.getenv("DELIVERYFLOW_TOKEN")
        if token:
            response = await client.get(
                "/api/v1/companies/",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            assert "items" in response.json()
            print("Company API authenticated list check passed")
        else:
            print("Company routes and health check passed; set DELIVERYFLOW_TOKEN for CRUD access")


if __name__ == "__main__":
    asyncio.run(main())