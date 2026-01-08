FROM node:25-alpine AS frontendbuild

COPY ./javascript /app
RUN --mount=type=cache,target=/root/.npm cd /app && npm ci && npm run build-frontend-prod

FROM python:3.10-alpine AS build

COPY ./requirements /requirements
RUN \
    --mount=type=cache,target=/var/cache/apk/ \
    apk add build-base curl \
    # psycopg2 dependencies
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add libpq-dev \
    # Pillow dependencies
    && apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev \
    # CFFI dependencies
    && apk add libffi-dev py-cffi \
    # XLSX dependencies
    && apk add libxml2-dev libxslt-dev \
    # Rust and Cargo required by the ``cryptography`` Python package
    && apk add rust cargo
RUN \
    --mount=type=cache,target=/root/.cache/pip \
    pip install wheel \
    && pip wheel --wheel-dir=/wheels --no-binary psycopg2 -r /requirements/production.txt

FROM python:3.10-alpine

RUN \
  --mount=type=cache,target=/var/cache/apk/ \
  apk add libpq

RUN \
  --mount=type=bind,target=/wheels,source=/wheels,from=build \
  --mount=type=bind,target=/requirements,source=/requirements,from=build \
  --mount=type=cache,target=/root/.cache/pip \
  pip install --find-links=/wheels -r /requirements/production.txt

RUN addgroup -S django && adduser -S -G django django

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
