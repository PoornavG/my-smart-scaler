FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    opentelemetry-distro \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-flask \
    opentelemetry-instrumentation-requests
COPY . .
EXPOSE 8080
# --- NEW Service Name ---
CMD ["opentelemetry-instrument", \
    "--service_name", "web-storefront", \
    "--traces_exporter", "otlp", \
    "--metrics_exporter", "none", \
    "--logs_exporter", "none", \
    "--exporter_otlp_traces_endpoint", "http://otel-collector.default:4317", \
    "python", "app.py"]