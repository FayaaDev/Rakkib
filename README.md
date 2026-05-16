# Rakkib

Rakkib is a personal server installer for fresh Ubuntu servers and MacOS. Pick from an open source library of more than 50+ tools and Rakkib will install it, render your config, and deploy it either on subdomain or locally.

## Install

```bash
curl -fsSL https://install.rakkib.app | bash
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


https://github.com/user-attachments/assets/ca819df9-1efe-48a7-9127-a747474dc4fb


## Requirements

- Ubuntu 24.04 is the tested production deployment target.
- macOS is supported for local CLI and web UI use.
- A sudo-capable admin user is recommended; avoid running as root unless you intentionally accept root-owned install paths.
- A Cloudflare-managed domain is required for public HTTPS routes.

## Development

This repository is the generated public runtime snapshot for Rakkib installs. Runtime releases are published from the private development repository and should not be edited here directly.

## License

MIT
