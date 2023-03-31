FROM python:3.10.9-alpine3.17

ENV PYTHONUNBUFFERED 1

ENV PYTHONDONTWRITEBYTECODE 1

RUN apk --no-cache add build-base curl \
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
    # Dependencies for scipy for custom code
    && apk --no-cache add gfortran openblas-dev \
    # Pull down Arial Narrow fonts from S3 bucket
    && mkdir -p /usr/local/share/fonts \
    && curl -O https://stratum-ghostwriter.s3.amazonaws.com/ArialNarrow.ttf --output-dir /usr/local/share/fonts \
    && curl -O https://stratum-ghostwriter.s3.amazonaws.com/ArialNarrowBold.ttf --output-dir /usr/local/share/fonts \
    && curl -O https://stratum-ghostwriter.s3.amazonaws.com/ArialNarrowBoldItalic.ttf --output-dir /usr/local/share/fonts \
    && curl -O https://stratum-ghostwriter.s3.amazonaws.com/ArialNarrowItalic.ttf --output-dir /usr/local/share/fonts \
    # Refresh the font cache with the new font installed
    && fc-cache -f \
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
