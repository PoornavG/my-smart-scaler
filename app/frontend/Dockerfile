# 1. Start from a lightweight Python base image
FROM python:3.9-slim

# 2. Set a working directory inside the container
WORKDIR /app

# 3. Copy only the requirements file first
COPY requirements.txt .

# 4. Install Python libraries (including OpenTelemetry)
RUN pip install --no-cache-dir \
    requests \
    flask \
    opentelemetry-distro \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-flask \
    opentelemetry-instrumentation-requests

# 5. Copy the rest of the application code
COPY . .

# 6. Expose the port the app runs on
EXPOSE 8080

# 7. This is the magic command to run the app WITH tracing
CMD ["opentelemetry-instrument", \
     "--service_name", "frontend-service", \
     "--traces_exporter", "otlp", \
     "--metrics_exporter", "none", \
     "--logs_exporter", "none", \
     "--exporter_otlp_traces_endpoint", "http://otel-collector.default:4317", \
     "python", "app.py"]