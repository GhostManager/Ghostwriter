FROM hasura/graphql-engine:v2.39.1.cli-migrations-v3

RUN rm -f /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./hasura-docker/metadata /metadata
