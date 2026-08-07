FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl libreoffice-writer fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./compose/production/middleware-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir uv \
    && uv pip install --system -r /app/requirements.txt

COPY ./compose/production/middleware-api/ /app/
# Custom fonts (e.g. Segoe UI) for DOCX→PDF rendering
RUN mkdir -p /usr/local/share/fonts/custom
COPY ./compose/production/middleware-api/fonts/ /usr/local/share/fonts/custom/
RUN fc-cache -f -v
RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

EXPOSE 8443

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
