"""Simple smoke test for Docker-based backend verification.

Run in container:
    python tests/docker_smoke_test.py

This script intentionally avoids pytest and uses plain asserts.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ok", payload

    api_response = client.get("/api/v1/")
    assert api_response.status_code in (200, 404), api_response.text

    print("SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
