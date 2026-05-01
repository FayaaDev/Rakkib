# Low-Friction Rakkib Service Candidates

This batch lists the additional services from `Services/` that should fit Rakkib's current registry-driven service structure with minimal custom code.

Classification guide:

- `A: static/simple web` - single web container, usually no database.
- `B: app + volume` - single app container with persistent config/data volumes.
- `C: app + shared Postgres` - can use Rakkib's shared Postgres pattern.
- `D: media/data app` - mostly volume-heavy media or library service.
- `E: admin/host-aware` - simple enough, but may need Docker socket, host metrics, or host mounts.

Total low-friction candidates: **83**.

Already represented in Rakkib and not counted here: `NocoDB`, `Homepage`, `Uptime Kuma`, `Dockge`, `n8n`, `Immich`, `Jellyfin`, `OpenClaw`.

| Category | Service | Classification |
|---|---|---|
| Dashboards | Dash. / Dashdot | E: admin/host-aware |
| Dashboards | Dashy | B: app + volume |
| Dashboards | Glance | B: app + volume |
| Dashboards | Heimdall | B: app + volume |
| Dashboards | Homarr | B: app + volume |
| Dashboards | Homer | A: static/simple web |
| Developer Tools | Atuin Server | C: app + shared Postgres |
| Developer Tools | Code Server | B: app + volume |
| Developer Tools | CyberChef | A: static/simple web |
| Developer Tools | IT-Tools | A: static/simple web |
| Developer Tools | Planning Poker | A: static/simple web |
| Books And Reading | Booksonic | D: media/data app |
| Books And Reading | Calibre-Web | D: media/data app |
| Books And Reading | Kavita | D: media/data app |
| Books And Reading | Komga | D: media/data app |
| Books And Reading | openbooks | B: app + volume |
| Books And Reading | PodFetch | D: media/data app |
| Books And Reading | Readarr | D: media/data app |
| Books And Reading | Suwayomi | D: media/data app |
| Monitoring | Beszel | E: admin/host-aware |
| Monitoring | Dozzle | E: admin/host-aware |
| Monitoring | Glances | E: admin/host-aware |
| Monitoring | Grafana | B: app + volume |
| Monitoring | Netdata | E: admin/host-aware |
| Personal And Lifestyle | DailyTxT | B: app + volume |
| Personal And Lifestyle | Flightlog | B: app + volume |
| Personal And Lifestyle | Grocy | B: app + volume |
| Personal And Lifestyle | Hammond | B: app + volume |
| Personal And Lifestyle | HomeBox | B: app + volume |
| Personal And Lifestyle | Koillection | B: app + volume |
| Personal And Lifestyle | LinkStack | B: app + volume |
| Personal And Lifestyle | LubeLogger | B: app + volume |
| Personal And Lifestyle | Mealie | C: app + shared Postgres |
| Personal And Lifestyle | Moodist | A: static/simple web |
| Personal And Lifestyle | Movary | B: app + volume |
| Personal And Lifestyle | PrivateBin | B: app + volume |
| Personal And Lifestyle | Stirling-PDF | B: app + volume |
| File Sync And Sharing | File Browser | B: app + volume |
| File Sync And Sharing | PairDrop | A: static/simple web |
| File Sync And Sharing | Pingvin Share | B: app + volume |
| File Sync And Sharing | Send | B: app + volume |
| File Sync And Sharing | Syncthing | B: app + volume |
| File Sync And Sharing | Zipline | B: app + volume |
| Search And RSS | FreshRSS | B: app + volume |
| Search And RSS | RSS | A: static/simple web |
| Search And RSS | RSSHub | A: static/simple web |
| Search And RSS | SearXNG | B: app + volume |
| Search And RSS | Whoogle Search | B: app + volume |
| Media Management | Bazarr | D: media/data app |
| Media Management | Kapowarr | D: media/data app |
| Media Management | Lidarr | D: media/data app |
| Media Management | Maintainerr | D: media/data app |
| Media Management | Mylar3 | D: media/data app |
| Media Management | Radarr | D: media/data app |
| Media Management | Sonarr | D: media/data app |
| Media Management | Tautulli | D: media/data app |
| Media Management | Wizarr | D: media/data app |
| Media Server | Audiobookshelf | D: media/data app |
| Media Server | mStream Music | D: media/data app |
| Media Server | Navidrome | D: media/data app |
| Media Server | Owncast | D: media/data app |
| Document And Knowledge | ChangeDetection | B: app + volume |
| Document And Knowledge | DokuWiki | B: app + volume |
| Document And Knowledge | flatnotes | B: app + volume |
| Document And Knowledge | Kiwix Server | D: media/data app |
| Document And Knowledge | Memos | B: app + volume |
| Document And Knowledge | Notemark | B: app + volume |
| Document And Knowledge | Silverbullet | B: app + volume |
| Document And Knowledge | Trilium | B: app + volume |
| Finance | Actual Budget | B: app + volume |
| Finance | Wallos | B: app + volume |
| Git And DevOps | Forgejo | C: app + shared Postgres |
| Git And DevOps | Gitea | C: app + shared Postgres |
| Git And DevOps | OneDev | B: app + volume |
| Remote Access | Hello World | A: static/simple web |
| Remote Access | Sshwifty | B: app + volume |
| Remote Access | Whoami | A: static/simple web |
| Secrets And Auth | 2FAuth | B: app + volume |
| Secrets And Auth | Vaultwarden | B: app + volume |
| Utility | LibreTranslate | B: app + volume |
| Calendar And Contacts | Baikal | B: app + volume |
| Diagram And Design | Draw.io | A: static/simple web |
| Diagram And Design | Excalidraw | A: static/simple web |
