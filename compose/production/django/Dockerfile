FROM node:21-alpine AS frontendbuild

COPY ./javascript /app
RUN --mount=type=cache,target=/root/.npm cd /app && npm ci && npm run build-frontend-prod

FROM python:3.10.9-alpine3.17

ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH="$PYTHONPATH:/app/config"

RUN \
    --mount=type=cache,target=/var/cache/apk/ \
    --mount=type=cache,target=/root/.cache/pip \
    apk add build-base curl \
    # psycopg2 dependencies
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add postgresql-dev \
    # Pillow dependencies
    && apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev \
    # CFFI dependencies
    && apk add libffi-dev py-cffi \
    # XLSX dependencies
    && apk add libxml2-dev libxslt-dev \
    # Rust and Cargo required by the ``cryptography`` Python package
    && apk add rust cargo \
    && addgroup -S django \
    && adduser -S -G django django \
    && pip install -U setuptools pip

COPY ./requirements /requirements

RUN --mount=type=cache,target=/root/.cache/pip pip install -r /requirements/production.txt \
    && rm -rf /requirements

COPY ./compose/production/django/entrypoint /entrypoint

RUN sed -i 's/\r$//g' /entrypoint \
    && chmod +x /entrypoint \
    && chown django /entrypoint

COPY ./compose/production/django/start /start

RUN sed -i 's/\r$//g' /start \
    && chmod +x /start \
    && chown django /start

COPY . /app

COPY ./compose/production/django/queue/start /start-queue

RUN sed -i 's/\r//' /start-queue \
    && chmod +x /start-queue \
    && chown django /start-queue

COPY ./compose/production/django/seed_data /seed_data

RUN sed -i 's/\r$//g' /seed_data \
    && chmod +x /seed_data \
    && mkdir -p /app/staticfiles \
    && mkdir -p /app/ghostwriter/media \
    && chown -R django /app

COPY --from=frontendbuild /app/dist_frontend /frontend

USER django

WORKDIR /app

VOLUME ["/app/ghostwriter/media", "/app/staticfiles"]

ENTRYPOINT ["/entrypoint"]
