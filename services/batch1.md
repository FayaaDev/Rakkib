# Batch 1 Rakkib Service Candidates

This first batch contains 20 low-friction services recommended for initial integration because they fit Rakkib's current service model cleanly and cover useful categories without requiring host installers, GPU/runtime variants, mail/DNS setup, VPN networking, or complex dependency stacks.

Classification guide:

- `A: static/simple web` - single web container, usually no database.
- `B: app + volume` - single app container with persistent config/data volumes.
- `C: app + shared Postgres` - can use Rakkib's shared Postgres pattern.
- `E: admin/host-aware` - simple enough, but may need Docker socket, host metrics, or host mounts.

| Priority | Category | Service | Git URL | Classification |
|---:|---|---|---|---|
| 1 | File Sync And Sharing | File Browser | https://github.com/filebrowser/filebrowser | B: app + volume |
| 2 | Developer Tools | IT-Tools | https://github.com/CorentinTh/it-tools | A: static/simple web |
| 3 | Developer Tools | CyberChef | https://github.com/gchq/CyberChef | A: static/simple web |
| 4 | Diagram And Design | Draw.io | https://github.com/jgraph/drawio | A: static/simple web |
| 5 | Diagram And Design | Excalidraw | https://github.com/excalidraw/excalidraw | A: static/simple web |
| 6 | Dashboards | Dashy | https://github.com/lissy93/dashy | B: app + volume |
| 7 | Dashboards | Glance | https://github.com/glanceapp/glance | B: app + volume |
| 8 | Dashboards | Homer | https://github.com/bastienwirtz/homer | A: static/simple web |
| 9 | Monitoring | Dozzle | https://github.com/amir20/dozzle | E: admin/host-aware |
| 10 | Monitoring | Beszel | https://github.com/henrygd/beszel | E: admin/host-aware |
| 11 | Finance | Actual Budget | https://github.com/actualbudget/actual | B: app + volume |
| 12 | Secrets And Auth | Vaultwarden | https://github.com/dani-garcia/vaultwarden | B: app + volume |
| 13 | Search And RSS | FreshRSS | https://github.com/FreshRSS/FreshRSS | B: app + volume |
| 14 | Search And RSS | RSSHub | https://github.com/DIYgod/RSSHub | A: static/simple web |
| 15 | Search And RSS | Whoogle Search | https://github.com/benbusby/whoogle-search | B: app + volume |
| 16 | Personal And Lifestyle | Mealie | https://github.com/hay-kot/mealie | C: app + shared Postgres |
| 17 | Personal And Lifestyle | Stirling-PDF | https://github.com/Frooodle/Stirling-PDF/ | B: app + volume |
| 18 | Personal And Lifestyle | PrivateBin | https://github.com/PrivateBin/PrivateBin | B: app + volume |
| 19 | Git And DevOps | Gitea | https://github.com/go-gitea/gitea | C: app + shared Postgres |
| 20 | Git And DevOps | Forgejo | https://codeberg.org/forgejo/forgejo/ | C: app + shared Postgres |
