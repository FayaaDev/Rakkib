# QR Login — Cloudflare Browser Auth for Headless Servers

## Problem

`cloudflared tunnel login` opens a browser on the local machine.
On a headless server this either fails silently or prints the URL with no
guidance. The user has to SSH in, read the URL, then manually paste it into a
browser on another device.

The fix: capture that URL and render a QR code directly in the terminal.
The user scans it with their phone, completes OAuth, `cloudflared` picks up
`cert.pem`, and the install continues.

---

## Scope

One file changes: `src/rakkib/steps/cloudflare.py`.
One new dependency: `qrcode[cli]` (added to `pyproject.toml`).
No new modules, no new state keys, no schema changes.

---

## Dependency

Add to `pyproject.toml` under `[project] dependencies`:

```toml
"qrcode[cli]>=7.4",
```

`qrcode[cli]` pulls in `colorama` on Windows only; no heavy transitive deps.
It ships a `qr` CLI entry-point, but we'll call the Python API directly so we
don't depend on PATH resolution inside the venv.

---

## Implementation — `cloudflare.py`

### New helper: `_show_qr(url: str) -> None`

```python
def _show_qr(url: str) -> None:
    try:
        import qrcode
        import qrcode.constants
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)   # white-on-black renders on dark terminals
    except ImportError:
        pass   # qrcode not installed; URL was already printed, that's enough
```

`print_ascii(invert=True)` works on any terminal (no ANSI colour codes needed)
and fits in ~60 columns for a typical Cloudflare dashboard URL.

### Changes to `run()` — `browser_login` branch

**Current (headless=True path):**
```python
print(
    "\nStep 40 is paused for Cloudflare approval.\n"
    "cloudflared tunnel login will print a URL.\n"
    "Open that URL on another signed-in device, approve the domain,\n"
    "then return here.\n"
)
result = subprocess.run(
    [_cloudflared_bin(), "tunnel", "login"],
    text=True,
)
```

**Replace with:**
```python
print("\nStep 40 — Cloudflare login (headless mode)")
print("Running: cloudflared tunnel login")
print("Waiting for auth URL...\n")

proc = subprocess.Popen(
    [_cloudflared_bin(), "tunnel", "login"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

login_url: str | None = None
assert proc.stdout is not None
for line in proc.stdout:
    print(line, end="", flush=True)
    if not login_url and "https://" in line:
        # cloudflared prints the URL on a line by itself
        login_url = line.strip().split()[-1]
        if login_url.startswith("https://"):
            print("\nScan this QR code on your phone to approve the domain:\n")
            _show_qr(login_url)
            print(
                f"\nOr open manually:\n  {login_url}\n\n"
                "Waiting for approval — keep this terminal open...\n"
            )

proc.wait()
if proc.returncode != 0:
    raise RuntimeError(
        f"cloudflared tunnel login failed (exit {proc.returncode}). "
        "Try again or use auth_method=api_token."
    )
```

The non-headless path (`headless=False`) is unchanged — it still hands off to
the blocking `subprocess.run` call and lets `cloudflared` open the system browser
directly.

---

## URL capture note

`cloudflared tunnel login` outputs something like:

```
Please open the following URL and log in with your Cloudflare account:
https://dash.cloudflare.com/argotunnel?aud=...&callback=...
Leave cloudflared running to download the cert automatically.
```

The grep approach (`split()[-1]` after checking for `https://`) is robust to
the exact wording changing as long as the URL is on its own line, which
`cloudflared` has done since v2020. A fallback `if login_url.startswith("https://"):`
guard drops any false positives.

---

## What does NOT change

- State schema — no new keys.
- The `api_token` and `existing_tunnel` branches — untouched.
- The non-headless browser-login path — untouched.
- `verify()` — untouched.
- `install.sh` — `qrcode[cli]` is installed via `pip install -e .` which is
  already how the venv is populated; no bootstrap changes needed.

---

## Testing

Manual test (can be done without a real Cloudflare account):

```bash
# In the Rakkib venv:
python - <<'EOF'
from rakkib.steps.cloudflare import _show_qr
_show_qr("https://example.com/test-qr-code-render")
EOF
```

Expected: a small QR code prints to stdout, scannable with a phone camera.

End-to-end: run `rakkib init` on a headless VM with `cloudflare.headless=true`
and `cloudflare.auth_method=browser_login`. Confirm the QR code appears before
the approval prompt, scan it, and verify the install continues after approval.

---

## Rollout

1. Add `qrcode[cli]>=7.4` to `pyproject.toml`.
2. Add `_show_qr()` to `cloudflare.py`.
3. Replace the headless `subprocess.run` block with the `Popen` streaming loop.
4. Manual test on a headless VM.
5. Merge as a single PR against `main`.
