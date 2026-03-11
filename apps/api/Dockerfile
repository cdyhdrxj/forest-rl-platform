FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev libpq5 && \
    rm -rf /var/lib/apt/lists/*

COPY packages/common/requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app:/app/apps/api
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]