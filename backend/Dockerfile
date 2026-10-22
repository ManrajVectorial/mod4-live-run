# Policy Assistant API. Build context is backend/, so the image carries the app AND the corpus.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CORPUS_DIR=/srv/backend/corpus

WORKDIR /srv/backend

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY corpus ./corpus

RUN useradd --system --no-create-home appuser
USER appuser

# Railway supplies PORT. There is no default: the container refuses to start without it.
CMD ["sh", "-c", "exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port ${PORT:?PORT must be set}"]
