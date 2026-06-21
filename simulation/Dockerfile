# =============================================================================
# Plant Simulator Dockerfile — NVIDIA AI Factory Controls
# =============================================================================
# Runs the plant physics simulator with NATS connectivity.
# Publishes telemetry to NATS as if it were the OPC UA bridges from real IPCs.
#
# Build: docker build -t aifactory-plant-sim ./simulation
# Run:   docker run --network host -e NATS_URL=nats://localhost:4222 aifactory-plant-sim
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="NVIDIA AI Factory Controls"
LABEL description="Plant physics simulator with NATS telemetry publishing"

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulation source
COPY plant_model/ ./plant_model/
COPY scenarios/ ./scenarios/
COPY run_all_scenarios.py .
COPY closed_loop.py .

# Copy fleet simulation (if present)
COPY fleet/ ./fleet/ 2>/dev/null || true

# Environment defaults
ENV NATS_URL=nats://nats:4222
ENV SITE_ID=us-west-01
ENV SCENARIO=training_ramp
ENV PUBLISH_RATE_HZ=10
ENV NUM_RACKS=8
ENV NUM_CDUS=2

# Run the plant simulator with NATS connection
CMD ["python", "-m", "plant_model.simulator", "--nats", "${NATS_URL}"]
