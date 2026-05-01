---
description: Add a Rakkib service from the services lists
---

You are working in the Rakkib repo. Implement the requested service(s) into Rakkib using the project skill `rakkib-add-service`.

Input: `$ARGUMENTS`

Rules:
- Follow @services/AGENTS.md and @services/rules.md.
- MUST use the skill at `.opencode/skills/rakkib-add-service/SKILL.md`.
- MUST validate on the test server via:
  `sshpass -p 'ub' ssh -o StrictHostKeyChecking=accept-new root@174.138.183.153`
- Validation must be the full bare-metal flow:
  `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`
  then `rakkib init`, then `rakkib pull`.

First, resolve what `$ARGUMENTS` refers to:
1. If it looks like a file path (ends with `.md`), read it and list the service names inside.
2. Otherwise treat it as a service name and locate it in the lists under `services/`.

Search results for the input:
!`rg -n --hidden -S "$ARGUMENTS" services/batch1.md services/batchx.md services/MoreServices || true`

Then:
- Add the service to `src/rakkib/data/registry.yaml`.
- Add required templates under `src/rakkib/data/templates/`.
- Add hook wiring only if required.
- Ensure `rakkib add` select+deselect works (including destructive removal).
- Run the required test-server validation and report what you verified.
