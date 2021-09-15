FROM python:3.8-alpine3.14

ENV PYTHONUNBUFFERED 1

ENV PYTHONDONTWRITEBYTECODE 1

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
    # Translations dependencies
    && apk --no-cache add gettext \
    # https://docs.djangoproject.com/en/dev/ref/django-admin/#dbshell
    && apk --no-cache add postgresql-client \
    # Rust and Cargo required by the ``cryptography`` Python package
    && apk --no-cache add rust \
    && apk --no-cache add cargo \
    && pip install --no-cache-dir -U setuptools pip

COPY ./requirements /requirements

RUN pip install --no-cache-dir -r /requirements/local.txt

COPY ./compose/production/django/entrypoint /entrypoint

RUN sed -i 's/\r$//g' /entrypoint \
    && chmod +x /entrypoint

COPY ./compose/local/django/start /start

RUN sed -i 's/\r$//g' /start \
    && chmod +x /start

COPY ./compose/production/django/queue/start /start-queue

RUN sed -i 's/\r//' /start-queue \
    && chmod +x /start-queue

COPY ./compose/local/django/seed_data /seed_data

RUN sed -i 's/\r$//g' /seed_data \
    && chmod +x /seed_data

WORKDIR /app

RUN mkdir -p /app/ghostwriter/media

VOLUME ["/app/ghostwriter/media"]

ENTRYPOINT ["/entrypoint"]
