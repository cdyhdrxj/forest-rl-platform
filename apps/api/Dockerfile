FROM python:3.10-slim

WORKDIR /app/api

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY packages/common/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]