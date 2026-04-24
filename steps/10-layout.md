# Step 10 — Layout

Create the target directory structure under `{{DATA_ROOT}}`.

## Actions

1. On Linux, create the managed `/srv` layout through the helper instead of creating root-owned paths directly from the unprivileged installer:
   `/usr/local/libexec/fayaasrv-root-helper ensure-linux-layout --admin-user {{ADMIN_USER}} [--with-service caddy] [--with-service cloudflared] [--with-service postgres] [--with-service nocodb] [--with-service n8n] [--with-service dbhub] [--with-service openclaw]`
2. On Mac, create these directories if they do not already exist:
   `{{DATA_ROOT}}/docker`, `{{DATA_ROOT}}/data`, `{{DATA_ROOT}}/apps/static`, `{{DATA_ROOT}}/backups`, and `{{DATA_ROOT}}/MDs`.
3. Create per-service directories only for required and selected services.
4. Ensure the admin user owns the created paths.
5. Create a placeholder root-site directory only if the user wants a static root site later.

## Verify

- `ls -ld {{DATA_ROOT}} {{DATA_ROOT}}/docker {{DATA_ROOT}}/data {{DATA_ROOT}}/backups {{DATA_ROOT}}/MDs`
- `test -w {{DATA_ROOT}}/docker`
