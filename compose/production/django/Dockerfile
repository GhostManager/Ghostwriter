FROM python:3.8-alpine

ENV PYTHONUNBUFFERED 1

ENV PYTHONPATH="$PYTHONPATH:/app/config"

RUN apk add build-base

RUN apk update \
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
    && apk add rust \
    && apk add cargo

RUN addgroup -S django \
    && adduser -S -G django django

# Requirements are installed here to ensure they will be cached
RUN pip install -U setuptools pip
COPY ./requirements /requirements
RUN pip install --no-cache-dir -r /requirements/production.txt \
    && rm -rf /requirements

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint
RUN chown django /entrypoint

COPY ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start
RUN chown django /start
COPY . /app

COPY ./compose/production/django/queue/start /start-queue
RUN sed -i 's/\r//' /start-queue
RUN chmod +x /start-queue
RUN chown django /start-queue

COPY ./compose/production/django/seed_data /seed_data
RUN sed -i 's/\r$//g' /seed_data
RUN chmod +x /seed_data

RUN mkdir -p /app/staticfiles

RUN chown -R django /app

USER django

WORKDIR /app

VOLUME ["/app/ghostwriter/media", "/app/staticfiles"]

ENTRYPOINT ["/entrypoint"]
