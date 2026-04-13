# Repository Guidelines

## Project Structure & Module Organization
`ghostwriter/` contains the Django application, split into app modules such as `api/`, `reporting/`, `rolodex/`, and `shepherd/`. Templates and static assets live under `ghostwriter/templates/` and `ghostwriter/static/`. Tests sit beside each app in `ghostwriter/*/tests/test_*.py`. Configuration entry points are `manage.py`, `config/settings/`, `local.yml`, and `production.yml`. Frontend and collaboration code lives in `javascript/src/frontend/` and `javascript/src/collab_server/`; generated GraphQL types are in `javascript/src/__generated__/`, and build output lands in `javascript/dist_*`. Long-form docs are in `DOCS/`.

## Build, Test, and Development Commands
Use Docker for the Django stack and `npm` only inside `javascript/`.

- Bootstrap the recommended local development environment with the platform-specific CLI binary: `./ghostwriter-cli-linux install --mode local-dev` on Linux, `./ghostwriter-cli-macos install --mode local-dev` on macOS, or `./ghostwriter-cli.exe install --mode local-dev` on Windows.
- `docker compose -f local.yml up -d` starts or refreshes the local services after config changes.
- `docker compose -f local.yml run --rm django python manage.py makemigrations && docker compose -f local.yml run --rm django python manage.py migrate` creates and applies schema changes.
- `docker compose -f local.yml run django coverage run manage.py test --exclude-tag=GitHub` runs the Python test suite the same way CI does.
- `cd javascript && npm run check` runs the TypeScript compiler with `--noEmit`.
- `cd javascript && npm run format` formats frontend sources with Prettier.
- `cd javascript && npm run codegen` regenerates GraphQL client artifacts after schema or query changes.

## Coding Style & Naming Conventions
Python uses 4-space indentation, `Black`, `isort`, and `flake8`. Follow the project docstring style in `DOCS/coding-style-guide/`, and keep imports grouped and sorted. JavaScript/TypeScript also uses 4-space indentation; Prettier enforces semicolons, double quotes, and the repository's line-ending settings. Use `snake_case` for Python modules and tests, `PascalCase` for React components, and keep test files named `test_<feature>.py`.

## Testing Guidelines
Add or update tests for every behavior change; PR templates require it. Prefer app-local tests in the matching `ghostwriter/<app>/tests/` package. For frontend GraphQL changes, regenerate `javascript/src/__generated__/` and run `npm run check` before opening a PR. Maintain coverage for touched code paths; CI uploads coverage from the Django suite.

## Commit & Pull Request Guidelines
Recent history favors short, imperative commit subjects such as `Corrected typo` or `Updated for GraphQL changes`. Keep commits narrowly scoped and describe the change, not the investigation. Pull requests should link the relevant issue, explain the design, note alternatives or drawbacks, describe verification steps, include a release-notes line, and pass all status checks. Include screenshots when UI behavior changes.
