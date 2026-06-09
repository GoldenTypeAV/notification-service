FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml .

RUN mkdir -p src/api src/shared src/worker && \
    touch src/api/__init__.py src/shared/__init__.py src/worker/__init__.py && \
    pip install --no-cache-dir -e .

COPY ./src ./src

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
