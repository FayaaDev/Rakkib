# Step 10 — Layout

Create the target directory structure under `{{DATA_ROOT}}`.

## Actions

1. Create these directories if they do not already exist:
   `{{DATA_ROOT}}/docker`, `{{DATA_ROOT}}/data`, `{{DATA_ROOT}}/apps/static`, `{{DATA_ROOT}}/backups`, and `{{DATA_ROOT}}/MDs`.
2. Create per-service directories only for required and selected services.
3. Ensure the admin user owns the created paths.
4. Create a placeholder root-site directory only if the user wants a static root site later.

## Verify

- `ls -ld {{DATA_ROOT}} {{DATA_ROOT}}/docker {{DATA_ROOT}}/data {{DATA_ROOT}}/backups {{DATA_ROOT}}/MDs`
- `test -w {{DATA_ROOT}}/docker`
