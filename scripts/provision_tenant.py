"""
provision_tenant.py — Repeatable tenant credential generator.

Creates a Tenant + `tenant_admin` user in one shot (email verified, active),
reusing the platform provisioning service. Idempotent: re-running with the
same email returns the existing credentials instead of failing.

Run inside the backend environment (it imports the app package):

    # Inside the backend container:
    docker exec -it df-backend python scripts/provision_tenant.py \\
        --email juniorflamebet@gmail.com \\
        --password 'Maurice@12!' \\
        --name 'Junior Flamebet' \\
        --business-type logistics

    # Defaults are provided, so this recreates the original tenant:
    docker exec -it df-backend python scripts/provision_tenant.py
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.deps import async_session
from app.models.enums import BusinessType
from app.services.tenant import provision_tenant


async def run(args: argparse.Namespace) -> int:
    try:
        business_type = BusinessType(args.business_type.lower())
    except ValueError:
        valid = ", ".join(b.value for b in BusinessType)
        print(f"Invalid --business-type. Choose one of: {valid}", file=sys.stderr)
        return 2

    async with async_session() as db:
        result = await provision_tenant(
            db,
            email=args.email,
            password=args.password,
            full_name=args.name,
            business_type=business_type,
        )

        status = "CREATED" if result.created else "ALREADY EXISTS"
        print(f"[{status}] Tenant credentials")
        print(f"  tenant_name   : {result.tenant.name}")
        print(f"  tenant_slug   : {result.tenant.slug}")
        print(f"  tenant_id     : {result.tenant.id}")
        print(f"  user_id       : {result.user.id}")
        print(f"  email         : {result.user.email}")
        print(f"  role          : {result.user.role}")
        print(f"  business_type : {result.tenant.business_type.value}")
        if result.created:
            print(f"  password      : {result.password}")
        print(f"  access_token  : {result.access_token}")

    # A non-zero code would fail CI/automation; idempotency is success.
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provision a DeliveryFlow tenant + admin user.")
    parser.add_argument("--email", default="juniorflamebet@gmail.com")
    parser.add_argument("--password", default="Maurice@12!")
    parser.add_argument("--name", default=None, help="Full name / tenant display name")
    parser.add_argument(
        "--business-type",
        default="logistics",
        choices=[b.value for b in BusinessType],
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args)))
