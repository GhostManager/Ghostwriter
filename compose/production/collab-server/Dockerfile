FROM --platform=$BUILDPLATFORM node:25.9.0-alpine3.23 AS build

WORKDIR /app
COPY ./javascript/package.json ./javascript/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY ./javascript /app
RUN npm run build-collab-server-prod

FROM node:25.9.0-alpine3.23

WORKDIR /app
COPY ./javascript/package.json ./javascript/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev
COPY --from=build /app/dist_collab_server ./dist_collab_server
ENTRYPOINT [ "npm", "run", "run-collab-server-prod" ]
