FROM node:21-alpine

COPY ./collab-server /app/collab-server
COPY ./tiptap-gw /app/tiptap-gw
COPY ./compose/production/collab-server/workspace.json /app/package.json
COPY ./package-lock.json /app/package-lock.json
RUN cd /app/collab-server && npm ci && npm run check

WORKDIR /app/collab-server
ENTRYPOINT [ "npm", "run", "run" ]
