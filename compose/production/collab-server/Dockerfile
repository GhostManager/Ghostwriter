FROM node:21-alpine

COPY ./javascript /app/
RUN cd /app/ && npm ci && npm run build-collab-server-prod

WORKDIR /app/
ENTRYPOINT [ "npm", "run", "run-collab-server" ]
