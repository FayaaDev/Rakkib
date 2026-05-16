# Rakkib

Rakkib is a personal server installer for fresh Ubuntu servers and MacOS. Choose from 50+ services and Rakkib will handle rendering, service configuration, and deployment (local or subdomain)

## Install

```bash
curl -fsSL https://install.rakkib.app | bash
```

Fallback:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/rakkib/main/install.sh | bash
```

Then run:

```bash
rakkib init
rakkib pull
```

## Update

```bash
rakkib update
```

## Requirements

- Ubuntu 24.04 is the tested production deployment target.
- macOS is supported for local CLI and web UI use.
- A sudo-capable admin user is recommended; avoid running as root unless you intentionally accept root-owned install paths.
- A Cloudflare-managed domain is required for public HTTPS routes.

## Development

This is a new project. Expect bugs. PRs are welcome. 
Recommend your favorite open source tool and it will be added.

## License

MIT
