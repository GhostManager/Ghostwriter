FROM busybox:1.36.1-uclibc AS healthcheck

FROM hasura/graphql-engine:v2.39.1.cli-migrations-v3

COPY --from=healthcheck /bin/busybox /usr/local/bin/busybox

COPY ./hasura-docker/metadata /metadata
