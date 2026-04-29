# Fix: `rakkib pull` succeeds but every hostname returns Cloudflare error 1033

## Context

The user ran `rakkib pull` on a fresh server and it completed successfully — the `cloudflared` container is up and `verify()` passes — but every hostname (apex + wildcard subdomains) returns Cloudflare error 1033 ("Argo Tunnel error: tunnel not running / DNS hostname not routed to a running tunnel").

Error 1033 is emitted by the Cloudflare edge when a DNS hostname's CNAME points at a tunnel UUID for which **no connector is currently registered**. The most common cause is a DNS CNAME left over from a previous tunnel, still pointing at an old `<old-uuid>.cfargotunnel.com`, while the running container is connected as a *different* tunnel.

Reading `src/rakkib/steps/cloudflare.py`, two recent changes interact to produce exactly this state:

1. **Recovery-on-rerun (commit `d57f54e`, lines 414–437):** when local credentials for the previously-recorded tunnel can't be found, Rakkib mints a brand-new tunnel named `<name>-<epoch>` and uses *its* UUID for the rest of the run.
2. **DNS route step (lines 499–522)** then tries `cloudflared tunnel route dns <new-uuid> <hostname>` for `domain`, `*.domain`, `<ssh_subdomain>.domain`. If the CNAME already exists (because the previous run created it pointing at the old UUID), cloudflared exits non-zero with stderr containing `"already exists"`. **`_is_benign_dns_route_error()` (lines 84–94) swallows this**, treating it as success — but the CNAME still resolves to the *old* tunnel UUID.

Net effect: `verify()` passes (container running + local metrics endpoint responsive), but the edge routes traffic to a tunnel that has no connector → 1033 across every service. There is no end-to-end "is the tunnel actually connected to the edge?" check anywhere in `verify()` (cloudflare.py:537+).

A second, simpler scenario produces the same symptom: a user previously had a tunnel for this domain in their Cloudflare account; on this fresh server, Rakkib created a new tunnel; the stale CNAMEs from the old tunnel still resolve to the old UUID. Same 1033, same root cause.

The intended outcome is: (a) diagnose definitively whether DNS/UUID drift is the culprit on this user's server; (b) make Rakkib robust against this in future runs by using cloudflared's canonical `--overwrite-dns` flag instead of suppressing the error.

## Files to modify

- `src/rakkib/steps/cloudflare.py` — DNS route loop (lines 499–522) and the `_is_benign_dns_route_error` helper (lines 84–94).

## Diagnosis (run on the bare-metal target server first)

These are read-only commands. They confirm the diagnosis before any code change.

```bash
# 1. What UUID is the running container actually serving?
docker exec cloudflared cat /home/nonroot/.cloudflared/config.yml | head -3
docker logs cloudflared --tail=50 | grep -E "Registered tunnel connection|tunnel ID|Unauthorized|error"

# 2. What UUID does DNS think the hostname points at?
dig +short claw.fayaa92.sa CNAME
dig +short fayaa92.sa CNAME
dig +short '*.fayaa92.sa' CNAME    # may need: dig +short test.fayaa92.sa CNAME

# 3. Cross-check with Cloudflare's view
cloudflared tunnel list
cloudflared tunnel info <uuid-from-step-1>
```

If the CNAME UUID in step 2 differs from the registered tunnel UUID in step 1, the diagnosis is confirmed: stale DNS routes pointing at a defunct tunnel.

## Immediate manual remediation (one-shot, on the affected server)

```bash
TUNNEL=$(grep '^tunnel:' /srv/data/cloudflared/config.yml | awk '{print $2}')
for h in fayaa92.sa '*.fayaa92.sa' claw.fayaa92.sa; do
  cloudflared tunnel route dns --overwrite-dns "$TUNNEL" "$h"
done
docker restart cloudflared
```

DNS propagation through Cloudflare's edge is near-instant; 1033 should clear within a minute.

## Code fix (so this can't recur)

Replace the suppress-on-"already exists" pattern with cloudflared's first-class `--overwrite-dns` flag, which atomically rewrites the CNAME to point at the supplied tunnel.

In `src/rakkib/steps/cloudflare.py` around lines 499–522:

```python
dns_routes = [domain, f"*.{domain}", f"{ssh_subdomain}.{domain}"]
for route in dns_routes:
    route_result = _run(
        [_cloudflared_bin(), "tunnel", "route", "dns", "--overwrite-dns",
         tunnel_uuid, route],
        env=token_env,
        check=False,
    )
    if route_result.returncode != 0:
        # Fallback: try with tunnel name (some cloudflared builds prefer name)
        route_result = _run(
            [_cloudflared_bin(), "tunnel", "route", "dns", "--overwrite-dns",
             tunnel_name, route],
            env=token_env,
            check=False,
        )
        if route_result.returncode != 0:
            raise RuntimeError(
                f"DNS route creation failed for {route}: "
                f"{route_result.stderr.strip() if route_result.stderr else 'unknown error'}"
            )
```

Then **delete `_is_benign_dns_route_error`** (lines 84–94). Suppression is no longer needed because `--overwrite-dns` makes the call idempotent: it rewrites whether or not a record exists. Keeping the helper would silently hide future bugs.

`--overwrite-dns` has been a stable cloudflared flag since 2021, so the version installed by `attempt_fix_cloudflared()` supports it.

## Optional hardening (recommended, same file)

Strengthen `verify()` (cloudflare.py:537+) so a future broken tunnel can't masquerade as healthy:

- After the metrics-endpoint check, parse `docker logs cloudflared --tail=200` and require at least one `Registered tunnel connection` line. That is cloudflared's own confirmation that it reached the edge and authenticated.
- Optionally check that `dig +short <domain> CNAME` returns `<tunnel_uuid>.cfargotunnel.com` — but this depends on the host having `dig`, so the log-grep is the more portable signal.

This is the smallest change that turns 1033 from a silent failure into a verification error.

## Verification

On a fresh Ubuntu 24.04 VM (per CLAUDE.md, do not test on this machine):

1. `bash install.sh` — runs cleanly.
2. `rakkib pull` to completion.
3. `dig +short fayaa92.sa CNAME` returns `<uuid>.cfargotunnel.com` matching the UUID in `/srv/data/cloudflared/config.yml`.
4. `curl -sS -o /dev/null -w "%{http_code}\n" https://fayaa92.sa` returns a non-1033 status (200/301/302/404 — anything other than the 530 page that wraps 1033).
5. `docker logs cloudflared --tail=50` contains at least one `Registered tunnel connection` line.
6. Re-run `rakkib pull` on the same server (idempotency check). DNS routes should rewrite cleanly to whatever tunnel is currently in use, and step 4 still passes.
7. To simulate the original bug deterministically: in Cloudflare dash, manually point the apex CNAME at a fake tunnel UUID, then run `rakkib pull`. With the fix, the route step rewrites it; without the fix, 1033 returns.
