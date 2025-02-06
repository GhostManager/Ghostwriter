You'll need to restart the collab-server container for changes to take effect.

If you edit a `gql` query, run `docker compose -f local.yml run --rm collab-server npm run codegen`

If you're on a Windows host, running `npm install` on the host will install the Windows dependencies for certain things like Sass, which will cause the commands inside of the containers (which run Linux) to fail. Play it safe and run npm commands in `docker compose -f local.yml run --rm collab-server (the-command)`.
