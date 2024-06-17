FROM hasura/graphql-engine:v2.39.1.cli-migrations-v3

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
