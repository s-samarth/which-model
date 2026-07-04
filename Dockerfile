FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY whichmodel ./whichmodel
COPY ingestion ./ingestion
COPY kb ./kb
COPY data ./data

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "whichmodel.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
