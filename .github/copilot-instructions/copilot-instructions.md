# Ghostwriter Copilot Instructions

## Repository Overview

**Ghostwriter** is an offensive security operations platform for report writing, asset tracking, and assessment management. Built with Python 3.10, Django 4.2, TypeScript/React in Docker containers. ~484 Python files, ~76 JS/TS files, 77MB codebase.

**Stack:** Django 4.2 | Python 3.10 | PostgreSQL 16.4 | Redis 6 | React/TypeScript | Vite | Hasura GraphQL v2.39.1 | Channels 4.0 WebSockets | Django-Q2 background tasks | Docker Compose | Jinja2/python-docx/python-pptx for reports

## Environment Setup

**Prerequisites:** Docker 28.0.4+, Docker Compose v2.38.2+, pre-built `ghostwriter-cli-linux` in repo root

**⚠️ CRITICAL:** Installation requires internet access to Alpine mirrors. Sandboxed environments will fail with "network error" - this is a known limitation.

**Setup (5-10 min first run):**
```bash
chmod +x ghostwriter-cli-linux
./ghostwriter-cli-linux install --dev  # Builds images, initializes DB
./ghostwriter-cli-linux up --dev       # Start (or: docker compose -f local.yml up -d)
./ghostwriter-cli-linux down --dev     # Stop (or: docker compose -f local.yml down)
```

**Container commands:** `containers up/down/restart/build --dev`, `running` (list services)

## Build, Test, and Development

### Live Development
Django auto-reloads with `local.yml` - **NO rebuild needed** for Python/template/static changes.

**Rebuild required for:** New dependencies in `requirements/*.txt`, new tasks in `tasks.py`, Dockerfile changes
```bash
docker compose -f local.yml stop && docker compose -f local.yml rm -f && docker compose -f local.yml build && docker compose -f local.yml up -d
```

### Migrations
**ALWAYS run after model changes:**
```bash
docker compose -f local.yml run --rm django python manage.py makemigrations
docker compose -f local.yml run --rm django python manage.py migrate
```

### Tests (~45-60s for full suite)
```bash
docker compose -f local.yml run django coverage run manage.py test  # All tests
docker compose -f local.yml run django coverage run manage.py test ghostwriter.rolodex.tests  # Specific app
./ghostwriter-cli-linux test --dev  # Using CLI
docker compose -f local.yml run django coverage report -m  # Coverage report
```
**Note:** Tests include intentional errors. Success = "OK" at end, no "FAILED".

### Linting & Code Quality
**Python:** Black (line length 90), isort (profile=black), flake8 (max 240/.pylintrc, 120/setup.cfg), pylint-django
```bash
docker compose -f local.yml run django black .
docker compose -f local.yml run django isort .
docker compose -f local.yml run django flake8
```

**JS/TS:** Prettier, TypeScript strict
```bash
cd javascript && npm install  # First time only
npm run check && npm run format  # Type check + format
npm run build-frontend-prod     # Production build
```

## Project Structure

**Root:** `manage.py`, `local.yml`/`production.yml` (Docker Compose), `.env`, `pytest.ini`, `setup.cfg`, `.pylintrc`, `.isort.cfg`, `.coveragerc`, `ghostwriter-cli-*`

**Django Apps** (`ghostwriter/`, each with models/views/urls/templates/tests):
- `reporting/` (1.7MB) - Report generation, templates, findings
- `rolodex/` (836KB) - Client/project management
- `shepherd/` (780KB) - Infrastructure/domain management
- `api/` (312KB) - REST API, GraphQL handlers
- `commandcenter/` (308KB) - Dashboard/statistics
- `oplog/` (272KB) - Activity logging
- `home/` (168KB) - Landing/user dashboard
- `users/` (168KB) - Auth/user management
- `modules/` (380KB) - Shared utilities
- `singleton/` (64KB) - Global config
- `status/` (36KB) - Health checks
- `static/` (9.9MB), `templates/` (300KB), `factories.py` (36KB)

**Config:** `config/settings/{base,local,production,test}.py`, `urls.py`, `asgi.py` (WebSockets), `wsgi.py`

**Frontend:** `javascript/src/` (TypeScript/React), `package.json`, `vite.config.*.ts`, `tsconfig.json`

**Docker:** `compose/local/` (Django/Node Dockerfiles), `compose/production/`

**GraphQL:** `hasura-docker/metadata/` (tables, actions, permissions)

## CI/CD

**GitHub Actions** (`.github/workflows/`):
1. **workflow.yml** - Main CI (push/PR to master): Builds dev env, runs tests with `--exclude-tag=GitHub`, uploads coverage to CodeCov (5-10 min)
2. **codeql-analysis.yml** - Security scan (Python/JS, push/PR/weekly Thu 6:31 AM)
3. **update-version.yml** - Version updates
4. **inactive-issues.yml** - Issue automation

**No pre-commit hooks.** Quality enforced via: manual linting → CI checks → code review

## Common Issues

1. **Container "stuck":** Django won't restart → `docker compose -f local.yml up -d`
2. **Alpine install fails:** "network error" → Known limitation, needs full internet access
3. **ImportError after adding deps:** → Rebuild containers (see above)
4. **Missing columns/tables:** → Run migrations (see above)
5. **Static files not loading:** → `docker compose -f local.yml run django python manage.py collectstatic --noinput`

**Logs:** `docker compose -f local.yml logs [django|queue|postgres|redis|graphql_engine]`, add `-f` to follow

## Key Dependencies

**Python:** Django 4.2, DRF 3.15.2, allauth 0.63.6 (SSO), allauth-2fa 0.11.1, Pillow 10.4.0, python-docx 1.1.2, python-pptx 1.0.2, docxtpl 0.18.0, jinja2 3.1.5, channels 4.0.0, django-q2 1.7.2, psycopg2, redis 5.0.8, boto3 1.35.17

**Dev:** pytest 7.3.1, pytest-django 4.5.2, coverage 7.2.7, black 23.3.0, flake8 6.0.0, pylint-django 2.5.3, mypy 1.2.0, factory-boy 3.2.1

**JS:** React 19.0.7, @apollo/client 3.13.1, @tiptap/* (editor), @hocuspocus/* (collab), Vite 5.4.10, TypeScript 5.7.3

## Testing & Utils

**Test structure:** `app/tests/{test_models,test_views,test_forms}.py` - Aim high coverage on business logic (`.coveragerc` excludes migrations/templates/admin/apps)

**Commands:**
```bash
docker compose -f local.yml run django python manage.py {shell|dbshell|createsuperuser}
./ghostwriter-cli-linux {tagcleanup|backup|healthcheck}
```

## Important Notes

1. **ALWAYS use `--dev`** with ghostwriter-cli for development
2. **NO force push** - git reset/rebase unsupported
3. **Style Guide:** https://ghostwriter.wiki/coding-style-guide/style-guide
4. **Code in `/app`** live-mounted from host
5. **DB persistent** (volume: `local_postgres_data`)
6. **Python 3.10.9** (Alpine 3.17)
7. **Default admin:** See `.env` file for credentials
8. **Only search if** error not documented, implementation details needed, or instructions outdated (current: v6.0.5, Oct 2025)
