# Step 50 — PostgreSQL

Deploy PostgreSQL and create one database/user pair per selected service.

## Actions

1. If `secrets.mode` is `generate`, generate and record any missing database secrets before rendering:
   - `POSTGRES_PASSWORD`
   - `NOCODB_DB_PASS`
   - `N8N_DB_PASS` if `n8n` is selected
2. Render `templates/docker/postgres/.env.example` into `{{DATA_ROOT}}/docker/postgres/.env` with the recorded `POSTGRES_PASSWORD`.
3. Create `{{DATA_ROOT}}/docker/postgres/init-scripts/init-services.sql`.
4. Always create the NocoDB database and role.
5. If `n8n` is selected, create the n8n database and role.
6. If `dbhub` is selected, no separate app database is required unless the user wants one; DBHub connects to Postgres directly.
7. Render `templates/docker/postgres/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/postgres/docker-compose.yml`.
8. Start PostgreSQL with `docker compose up -d` from `{{DATA_ROOT}}/docker/postgres`.

## SQL Expectations

The rendered SQL file should:

- create roles only if they do not exist
- create databases only if they do not exist
- grant ownership of each service database to its matching role

## Verify

- `docker ps | grep postgres`
- `docker exec postgres pg_isready -U postgres`
- `docker exec postgres psql -U postgres -c '\l'`
