#!/bin/sh
# =============================================================================
# SCADA Entrypoint — Start backend API + nginx frontend server
# =============================================================================

set -e

echo "Starting SCADA Backend (port ${PORT:-4000})..."
cd /app/backend
node server.js &
BACKEND_PID=$!

echo "Starting SCADA Frontend (nginx, port ${FRONTEND_PORT:-3001})..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "SCADA services running:"
echo "  Backend API:  http://localhost:${PORT:-4000}"
echo "  Frontend UI:  http://localhost:${FRONTEND_PORT:-3001}"

# Wait for either process to exit
wait -n $BACKEND_PID $NGINX_PID
exit $?
