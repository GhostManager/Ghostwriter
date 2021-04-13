FROM python:3.8-alpine

ENV PYTHONUNBUFFERED 1

ENV PYTHONDONTWRITEBYTECODE 1

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
    # Translations dependencies
    && apk add gettext \
    # https://docs.djangoproject.com/en/dev/ref/django-admin/#dbshell
    && apk add postgresql-client \
    # Rust and Cargo required by the ``cryptography`` Python package
    && apk add rust \
    && apk add cargo

# Requirements are installed here to ensure they will be cached
RUN pip install -U setuptools pip
COPY ./requirements /requirements
RUN pip install -r /requirements/local.txt

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/local/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./compose/production/django/queue/start /start-queue
RUN sed -i 's/\r//' /start-queue
RUN chmod +x /start-queue

COPY ./compose/local/django/seed_data /seed_data
RUN sed -i 's/\r$//g' /seed_data
RUN chmod +x /seed_data

WORKDIR /app

VOLUME ["/app/ghostwriter/media"]

ENTRYPOINT ["/entrypoint"]
