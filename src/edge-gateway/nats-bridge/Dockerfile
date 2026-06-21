FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bridges/opcua_nats_bridge.py .
COPY config/ ./config/
CMD ["python", "opcua_nats_bridge.py"]
