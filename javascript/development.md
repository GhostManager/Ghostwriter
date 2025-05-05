
# Subprojects

## `src/frontend`

Contains some more recent frontend JS code, such as the collaborative editing forms. Some other functionality lives in statis files under `/ghostwriter/static/` instead (though they should be moved to here eventually).

On a development setup, the `frontend` container will monitor and re-transpile files automatically if it's running. Simply refresh the page after edits (but see the note about graphql below). The exception is adding/removing NPM packages or editing the `vite.config.*.ts` files.

On a production setup, rebuild and restart the django container.

## `src/collab_server`

[Hocuspocus](https://tiptap.dev/docs/hocuspocus/introduction)-based collaborative editing server. Loads and saves documents via the graphql API, converting them to and from YJS.

It does not auto-reload code changes - restart the container after making code edits.

# GraphQL Codegen

If you add/edit a graphql query (a call to the `gql` function), you will need to run the code generator. Ensure the `graphql_engine` container is running, then run `docker compose -f local.yml run --rm frontend npm run codegen`

# Checking and Formatting

To typecheck, run `docker compose -f local.yml run --rm frontend npm run check`. Be sure to run graphql codegen if needed before running this.

To format, run `docker compose -f local.yml run --rm frontend npm run format`.

It is recommended to do both before committing changes.
