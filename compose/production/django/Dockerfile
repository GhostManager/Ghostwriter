FROM python:3.10.9-alpine3.17

ENV PYTHONUNBUFFERED 1

ENV PYTHONPATH="$PYTHONPATH:/app/config"

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
    # Rust and Cargo required by the ``cryptography`` Python package
    && apk --no-cache add rust \
    && apk --no-cache add cargo \
    # Nmap required by the ``python-nmap`` Python package. libcap used to set the capabilities of nmap so root is not required
    && apk --no-cache add nmap libcap \
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

RUN chown django:django /usr/bin/nmap \
    && chmod 750 /usr/bin/nmap

RUN setcap cap_net_raw,cap_net_bind_service+eip /usr/bin/nmap

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
