FROM python:3.12-slim

WORKDIR /srv/app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --extra embed --extra render

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV PATH="/srv/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
