#!/bin/bash
# =============================================================================
# JetStream Stream Initialization — NVIDIA AI Factory Controls
# =============================================================================
# Creates JetStream streams for telemetry, alarms, commands, config, and status.
# Run after NATS server is ready. Idempotent — safe to re-run.
#
# Usage: ./init-streams.sh [NATS_URL]
# =============================================================================

set -euo pipefail

NATS_URL="${1:-nats://localhost:4222}"
NATS_USER="${NATS_INIT_USER:-cloud-bridge}"
NATS_PASS="${NATS_INIT_PASS:-}"
MAX_RETRIES=30
RETRY_INTERVAL=2

# Build auth flag if credentials provided
AUTH_FLAG=""
if [ -n "$NATS_PASS" ]; then
  AUTH_FLAG="--user=$NATS_USER --password=$NATS_PASS"
fi

echo "Waiting for NATS server at ${NATS_URL}..."
for i in $(seq 1 $MAX_RETRIES); do
  if nats server ping --server="$NATS_URL" $AUTH_FLAG >/dev/null 2>&1; then
    echo "NATS server is ready."
    break
  fi
  if [ "$i" -eq "$MAX_RETRIES" ]; then
    echo "ERROR: NATS server not reachable after ${MAX_RETRIES} attempts."
    exit 1
  fi
  sleep $RETRY_INTERVAL
done

echo "Creating JetStream streams..."

# ─── Stream: Telemetry (all process data) ─────────────────────────────────
nats stream add TELEMETRY \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.telemetry.>" \
  --retention=limits \
  --max-age=24h \
  --max-bytes=5368709120 \
  --storage=file \
  --replicas=1 \
  --discard=old \
  --dupe-window=2m \
  --defaults \
  2>/dev/null || echo "Stream TELEMETRY already exists, updating..."

nats stream update TELEMETRY \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.telemetry.>" \
  --retention=limits \
  --max-age=24h \
  --max-bytes=5368709120 \
  --storage=file \
  --replicas=1 \
  --discard=old \
  --dupe-window=2m \
  --force \
  2>/dev/null || true

echo "  ✓ TELEMETRY stream (24h retention, 5GB max)"

# ─── Stream: Alarms (all alarm events) ───────────────────────────────────
nats stream add ALARMS \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.alarms.>" \
  --retention=limits \
  --max-age=168h \
  --storage=file \
  --replicas=1 \
  --discard=old \
  --defaults \
  2>/dev/null || echo "Stream ALARMS already exists, updating..."

nats stream update ALARMS \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.alarms.>" \
  --retention=limits \
  --max-age=168h \
  --storage=file \
  --replicas=1 \
  --discard=old \
  --force \
  2>/dev/null || true

echo "  ✓ ALARMS stream (7d retention)"

# ─── Stream: Commands (cloud → IPC) ──────────────────────────────────────
nats stream add COMMANDS \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.commands.>" \
  --retention=workqueue \
  --max-age=1h \
  --storage=file \
  --replicas=1 \
  --defaults \
  2>/dev/null || echo "Stream COMMANDS already exists, updating..."

nats stream update COMMANDS \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.commands.>" \
  --retention=workqueue \
  --max-age=1h \
  --storage=file \
  --replicas=1 \
  --force \
  2>/dev/null || true

echo "  ✓ COMMANDS stream (work-queue, 1h max-age)"

# ─── Stream: Config (parameter/setpoint changes) ─────────────────────────
nats stream add CONFIG \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.config.>" \
  --retention=limits \
  --max-msgs-per-subject=1 \
  --storage=file \
  --replicas=1 \
  --defaults \
  2>/dev/null || echo "Stream CONFIG already exists, updating..."

nats stream update CONFIG \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.config.>" \
  --retention=limits \
  --max-msgs-per-subject=1 \
  --storage=file \
  --replicas=1 \
  --force \
  2>/dev/null || true

echo "  ✓ CONFIG stream (last-value-per-subject)"

# ─── Stream: Status (IPC health heartbeats) ──────────────────────────────
nats stream add STATUS \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.status" \
  --retention=limits \
  --max-msgs-per-subject=1 \
  --storage=memory \
  --replicas=1 \
  --defaults \
  2>/dev/null || echo "Stream STATUS already exists, updating..."

nats stream update STATUS \
  --server="$NATS_URL" $AUTH_FLAG \
  --subjects="aifactory.*.*.status" \
  --retention=limits \
  --max-msgs-per-subject=1 \
  --storage=memory \
  --replicas=1 \
  --force \
  2>/dev/null || true

echo "  ✓ STATUS stream (memory, last-value-per-subject)"

echo ""
echo "All JetStream streams provisioned successfully."
nats stream ls --server="$NATS_URL" $AUTH_FLAG
