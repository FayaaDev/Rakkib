# Step 50 — PostgreSQL

Deploy PostgreSQL and create one database/user pair per selected service.

## Actions

1. Render `templates/docker/postgres/.env.example` into `{{DATA_ROOT}}/docker/postgres/.env` with a real `POSTGRES_PASSWORD`.
2. Create `{{DATA_ROOT}}/docker/postgres/init-scripts/init-services.sql`.
3. Always create the NocoDB database and role.
4. If `n8n` is selected, create the n8n database and role.
5. If `dbhub` is selected, no separate app database is required unless the user wants one; DBHub connects to Postgres directly.
6. Render `templates/docker/postgres/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/postgres/docker-compose.yml`.
7. Start PostgreSQL with `docker compose up -d` from `{{DATA_ROOT}}/docker/postgres`.

## SQL Expectations

The rendered SQL file should:

- create roles only if they do not exist
- create databases only if they do not exist
- grant ownership of each service database to its matching role

## Verify

- `docker ps | grep postgres`
- `docker exec postgres pg_isready -U postgres`
- `docker exec postgres psql -U postgres -c '\l'`
