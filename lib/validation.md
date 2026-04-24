# Post-Step Validation Checklist

This file documents the validation checks to run after each deployment step. All checks should be run by the agent and verified to pass before proceeding to the next step.

---

## After Step 00: Prerequisites

Validate that required tools are installed and versions meet minimum requirements.

### docker --version
```bash
docker --version
```
**Expected:** Output version string ≥ 24  
**Fail condition:** Command not found or version < 24  
**Example:** `Docker version 24.0.7, build afdd53b`

---

### docker compose version
```bash
docker compose version
```
**Expected:** Outputs compose version (≥ v2.x)  
**Fail condition:** Command not found or fails  
**Example:** `Docker Compose version v2.20.2`

---

### curl --version
```bash
curl --version
```
**Expected:** Outputs curl version  
**Fail condition:** Command not found  
**Example:** `curl 7.68.0 (x86_64-pc-linux-gnu) libcurl/7.68.0`

---

### cloudflared version
```bash
cloudflared --version
```
**Alternative (if cloudflared not installed):**
```bash
docker pull cloudflare/cloudflared:latest
```
**Expected:** cloudflared binary present OR docker image pulls successfully  
**Fail condition:** Both cloudflared binary unavailable AND docker pull fails  
**Example:** `cloudflared version 2024.4.1`

---

## After Step 10: Layout

Validate that directory structure is created correctly.

### Directories exist
```bash
ls -ld {{DATA_ROOT}}/docker {{DATA_ROOT}}/data {{DATA_ROOT}}/backups
```
**Expected:** All three directories exist with proper permissions  
**Fail condition:** Any directory missing or inaccessible  
**Example:**
```
drwxrwxr-x 5 user user 4096 Apr 24 10:00 {{DATA_ROOT}}/docker
drwxrwxr-x 5 user user 4096 Apr 24 10:00 {{DATA_ROOT}}/data
drwxrwxr-x 5 user user 4096 Apr 24 10:00 {{DATA_ROOT}}/backups
```

---

## After Step 20: Network

Validate that Docker network is created and functional.

### Docker network exists
```bash
docker network inspect {{DOCKER_NET}}
```
**Expected:** Returns JSON output describing the network  
**Fail condition:** `Error: No such network` or error response  
**Notes:** Network name substituted from .fss-state.yaml  
**Example output includes:**
```json
{
  "Name": "caddy_default",
  "Driver": "bridge",
  "Containers": {}
}
```

---

## After Step 30: Caddy

Validate that Caddy reverse proxy container is running and responding.

### Caddy container running
```bash
docker ps | grep caddy
```
**Expected:** Shows caddy container in running state  
**Fail condition:** No output or container not running  
**Example:** `<container_id>  caddy  "caddy run --config..."  Up 2 minutes`

---

### Caddy responds to HTTP
```bash
curl -s http://localhost/
```
**Expected:** HTTP response (200, 404, or error page, NOT connection refused)  
**Fail condition:** Connection refused or timeout  
**Notes:** Health check endpoint at `/health` returns "OK 200"  
**Example:** 
```bash
curl -s http://localhost/health
# Expected: OK
```

---

## After Step 40: Cloudflare Tunnel

Validate that cloudflared tunnel is running and credentials are configured.

### Paste tunnel UUID confirmation
**Manual step:** Operator must verify and paste the tunnel UUID back into `.fss-state.yaml`

**Expected state before proceeding:**
- `.fss-state.yaml` contains `tunnel_uuid: <UUID>` 
- Tunnel credentials file exists at `{{DATA_ROOT}}/data/cloudflared/credentials.json`
- File permissions are `600` (secret)

---

### cloudflared container running
```bash
docker ps | grep cloudflared
```
**Expected:** Shows cloudflared container in running state  
**Fail condition:** No output or container not running  
**Example:** `<container_id>  cloudflare/cloudflared  "cloudflared tunnel..."  Up 1 minute`

---

## After Step 50: PostgreSQL

Validate that PostgreSQL database is running, accepting connections, and all service databases exist.

### PostgreSQL accepting connections
```bash
docker exec postgres pg_isready -U postgres
```
**Expected:** `accepting connections`  
**Fail condition:** `rejecting connections` or error  
**Example:** `accepting connections`

---

### Service databases created
```bash
docker exec postgres psql -U postgres -c '\l'
```
**Expected:** List of databases includes configured service databases  
**Fail condition:** Expected databases not in list  
**Per-selected service, verify database exists:**
- **If nocodb selected:** `nocodb_db` exists
- **If n8n selected:** `n8n_db` exists
- **If other services selected:** Corresponding `<svc>_db` exists

**Example output:**
```
Name    |  Owner   | Encoding | Collate | Ctype
--------+----------+----------+---------+-------
n8n_db  | n8n_user | UTF8     | C       | C
nocodb_db | nocodb_user | UTF8   | C       | C
postgres| postgres | UTF8     | C       | C
```

---

## After Step 60: Service Deployment

Validate that selected services are running and reachable internally.

### Per-service container running
For each enabled optional service:
```bash
docker ps | grep <service_name>
```
**Expected:** Container shows in running state  
**Fail condition:** No output or container not running  

**Services to check (if selected):**
- nocodb: `docker ps | grep nocodb`
- n8n: `docker ps | grep n8n`
- changedetection: `docker ps | grep changedetection`
- seharadar: `docker ps | grep seharadar`
- superset: `docker ps | grep superset`
- lightrag: `docker ps | grep lightrag`
- (others as deployed)

---

### Services reachable via Caddy (internal)
```bash
curl -s http://localhost
```
**Expected:** Caddy routes to service or returns valid response  
**Fail condition:** Connection refused or timeout  
**Notes:** Verify services can reach each other through caddy network; test subset of high-value services

---

## After Step 90: Verification

Validate end-to-end connectivity through Cloudflare tunnel to public HTTPS endpoints.

### HTTPS response from root domain
```bash
curl -s https://{{DOMAIN}}/ -I
```
**Expected:** HTTP 200, 301, or service-specific response (not connection refused)  
**Fail condition:** Connection refused, timeout, or certificate error  
**Example:**
```
HTTP/2 200
content-type: text/html
```

---

### Per-service HTTPS endpoint (external)
For each deployed optional service:
```bash
curl -s https://{{SVC}}.{{DOMAIN}}/ -I
```
**Services to check (if selected):**
- nocodb: `curl -s https://nocodb.{{DOMAIN}}/ -I`
- n8n: `curl -s https://n8n.{{DOMAIN}}/ -I`
- changedetection: `curl -s https://changedetection.{{DOMAIN}}/ -I`
- claw: `curl -s https://claw.{{DOMAIN}}/ -I`
- (others as deployed)

**Expected:** HTTP 2xx, 3xx, or service-specific response  
**Fail condition:** Connection refused, 502 Bad Gateway, certificate error  

---

### All expected containers running
```bash
docker ps
```
**Expected:** All expected containers show in running state  
**Fail condition:** Missing containers or any in stopped/exited state  

**Minimum expected (core):**
- caddy
- postgres
- cloudflared

**Conditional on selection:**
- nocodb (if enabled)
- n8n (if enabled)
- changedetection (if enabled)
- seharadar (if enabled)
- superset (if enabled)
- lightrag (if enabled)
- (others as selected)

---

## Summary

**Total validation checkpoints:** 14+

**Flow:**
1. Prerequisites check (4 checks)
2. Layout verify (1 check)
3. Network verify (1 check)
4. Caddy running & responsive (2 checks)
5. Cloudflare tunnel running & credentials confirmed (2 checks + manual)
6. PostgreSQL running & databases created (2 checks)
7. Services running & internally reachable (2 checks)
8. End-to-end HTTPS verification (3+ checks)

**Failure handling:** If any check fails, stop the current step and debug before proceeding. All checks must pass before advancing to the next step.
