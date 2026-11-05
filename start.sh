#!/bin/bash
# Starts what this container runs. APP_ROLE selects it:
#   all     (default) the site on PORT, and the nightly worker beside it with its summary on WORKER_PORT (8081)
#   web     the site only, on PORT
#   worker  the worker only, its JSON summary on PORT
set -u
PORT="${PORT:-8080}"
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
