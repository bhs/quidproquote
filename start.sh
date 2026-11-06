#!/bin/bash
# Starts what this container runs. APP_ROLE selects it:
#   all     (default) the site on PORT, and the nightly worker beside it with its summary on WORKER_PORT (8081),
#           both on the one SQLite file at DATABASE_PATH
#   web     the site only, on PORT
#   worker  the worker only, its JSON summary on PORT (it needs the same file, so on the same disk as the site)
set -u
PORT="${PORT:-8080}"

# The database file lives on the disk at DATABASE_PATH's folder, which may be mounted owned by root: take it for
# the app user and carry on as that user.
if [ "$(id -u)" = "0" ]; then
  if [ -n "${DATABASE_PATH:-}" ]; then
    data_dir="$(dirname "$DATABASE_PATH")"
    mkdir -p "$data_dir" && chown -R app "$data_dir"
  fi
  exec setpriv --reuid=app --regid=app --init-groups "$0" "$@"
fi

case "${APP_ROLE:-all}" in
  web)
    exec uvicorn pairing_site.app:app --host 0.0.0.0 --port "$PORT" --no-access-log --log-level warning ;;
  worker)
    exec python -m pairing_site.worker ;;
  all)
    WORKER_PORT="${WORKER_PORT:-8081}" python -m pairing_site.worker &
    worker=$!
    uvicorn pairing_site.app:app --host 0.0.0.0 --port "$PORT" --no-access-log --log-level warning &
    web=$!
    trap 'kill "$worker" "$web" 2>/dev/null' TERM INT
    wait -n
    code=$?
    kill "$worker" "$web" 2>/dev/null
    wait
    exit "$code" ;;
  *)
    echo "APP_ROLE must be all, web or worker" >&2
    exit 2 ;;
esac
