#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h postgres -p 5432 -U df_user -d deliveryflow -q; do
  sleep 1
done
echo "PostgreSQL is ready."

# If a command is passed (e.g. "alembic upgrade head" for the migrate service,
# or "taskiq worker ..." for the taskiq-worker service), run it.
# Otherwise start the API application.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
