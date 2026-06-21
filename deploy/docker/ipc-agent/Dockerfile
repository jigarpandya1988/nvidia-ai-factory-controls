# =============================================================================
# IPC Monitoring Agent — Runs on each physical IPC alongside CODESYS
# =============================================================================
# This container runs ON the IPC (Linux) and provides:
#   1. Log shipping (CODESYS logs → CloudWatch)
#   2. Resource monitoring (CPU, RAM, disk → CloudWatch metrics)
#   3. Deployment agent (receives IoT Jobs, applies CODESYS updates)
#   4. Health reporting (heartbeat to AWS IoT Core)
# =============================================================================

FROM debian:bookworm-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    python3 \
    python3-pip \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Install AWS IoT Greengrass Lite (for IoT Jobs + log shipping)
# Alternative: custom Python agent (lighter weight)
RUN pip3 install --no-cache-dir \
    awsiotsdk==1.21.0 \
    boto3==1.34.0 \
    psutil==5.9.8 \
    watchdog==4.0.0 \
    pyyaml==6.0.1

# Copy agent code
COPY agent/ /opt/ipc-agent/
COPY config/ /opt/ipc-agent/config/

WORKDIR /opt/ipc-agent

# Agent runs as non-root
RUN useradd -r -s /bin/false agent
USER agent

ENTRYPOINT ["python3", "main.py"]
