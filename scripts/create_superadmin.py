"""
create_superadmin.py — Seed a platform super-admin.

Idempotent: if the user already exists, it is promoted to `super_admin` and
its password is reset to the provided value so the seed credentials always
work. This unlocks the `POST /api/v1/platform/tenants` provisioning API.

Run inside the backend environment:

    docker exec -it df-backend python scripts/create_superadmin.py \\
        --email juniorflamebet@gmail.com --password 'Maurice@12!'

Defaults match the requested seed account, so this suffices:

    docker exec -it df-backend python scripts/create_superadmin.py
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.deps import async_session
from app.services.tenant import ensure_superadmin


async def run(args: argparse.Namespace) -> int:
    async with async_session() as db:
        result = await ensure_superadmin(
            db,
            email=args.email,
            password=args.password,
            full_name=args.name,
        )

    status = "CREATED" if result.created else "PROMOTED/UPDATED"
    print(f"[{status}] Super-admin")
    print(f"  user_id    : {result.user.id}")
    print(f"  email      : {result.user.email}")
    print(f"  role       : {result.user.role}")
    print(f"  is_active  : {result.user.is_active}")
    print(f"  password   : {result.password}")
    print(f"  access_token: {result.access_token}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed a DeliveryFlow super-admin.")
    parser.add_argument("--email", default="juniorflamebet@gmail.com")
    parser.add_argument("--password", default="Maurice@12!")
    parser.add_argument("--name", default=None)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args)))
