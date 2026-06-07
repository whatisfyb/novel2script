# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN addgroup --system novel && adduser --system --ingroup novel novel
USER novel
EXPOSE 8000 8001 8002 8003
CMD ["uvicorn", "services.orchestrator:app", "--host", "0.0.0.0", "--port", "8000"]
