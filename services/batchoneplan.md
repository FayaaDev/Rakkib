**Plan**

1. Create/claim a beads task for `batch1.md` service deployment.
2. Add services in priority order using the mandatory `rakkib-add-service` workflow.
3. Implement in small deployable waves, not all 20 in one unverified change:
   - Wave 1: File Browser, IT-Tools, CyberChef, Draw.io, Excalidraw
   - Wave 2: Dashy, Glance, Homer, Dozzle, Beszel
   - Wave 3: Actual Budget, Vaultwarden, FreshRSS, RSSHub, Whoogle
   - Wave 4: Mealie, Stirling-PDF, PrivateBin, Gitea, Forgejo
4. For each service:
   - Add `registry.yaml` entry.
   - Add Docker `.env.example` and compose template.
   - Add Caddy route template.
   - Update `03-services.md` menu, aliases, placeholders.
   - Add hooks only if required.
   - Update tests/fixtures/snapshots if needed.
5. Validate registry/template consistency locally only as a sanity check, but not as proof.
6. Run required bare-metal validation on the test server:
   - `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`
   - `rakkib init`
   - `rakkib pull`
   - verify `rakkib add` select/deselect and removal behavior.
7. Commit and push changes before calling the work complete.

**Key Constraint**

The project rules require testing on `root@174.138.183.153` and pushing the finished branch before considering the deployment complete.
