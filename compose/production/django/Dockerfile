FROM python:3.8-alpine3.14

ENV PYTHONUNBUFFERED 1

ENV PYTHONPATH="$PYTHONPATH:/app/config"

RUN apk --no-cache add build-base \
    # psycopg2 dependencies
    && apk --no-cache add --virtual build-deps gcc python3-dev musl-dev \
    && apk --no-cache add postgresql-dev \
    # Pillow dependencies
    && apk --no-cache add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev \
    # CFFI dependencies
    && apk --no-cache add libffi-dev py-cffi \
    # XLSX dependencies
    && apk --no-cache add libxml2-dev libxslt-dev \
    # Rust and Cargo required by the ``cryptography`` Python package
    && apk --no-cache add rust \
    && apk --no-cache add cargo \
    && addgroup -S django \
    && adduser -S -G django django \
    && pip install --no-cache-dir -U setuptools pip

COPY ./requirements /requirements

RUN pip install --no-cache-dir -r /requirements/production.txt \
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

USER django

WORKDIR /app

VOLUME ["/app/ghostwriter/media", "/app/staticfiles"]

ENTRYPOINT ["/entrypoint"]
