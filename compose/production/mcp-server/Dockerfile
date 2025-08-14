FROM python:3.10.9-alpine3.17

ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH="$PYTHONPATH:/app/config"

RUN apk --no-cache add build-base curl \
    && addgroup -S mcp \
    && adduser -S -G mcp mcp \
    && pip install --no-cache-dir -U setuptools pip

COPY ./requirements /requirements

RUN pip install --no-cache-dir -r /requirements/mcp_requirements.txt \
    && rm -rf /requirements

COPY . /app

USER mcp

WORKDIR /app

ENTRYPOINT [ "python", "server.py", "--host", "0.0.0.0", "--port", "3001" ]