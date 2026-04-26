# VErgo Clean Integration Plan

## Goal

Integrate VErgo into Rakkib as an optional, Rakkib-native host addon that preserves Rakkib's interview -> state -> render -> verify flow.

This integration should not treat VErgo as a normal app service. It should be implemented as host customization for the admin user's shell and, on macOS only, an optional desktop/window-manager layer.

## Product Shape

Implement VErgo as two separate optional features:

1. `vergo_terminal`
2. `vergo_macos_wm`

`vergo_terminal` should support Linux and Mac.

`vergo_macos_wm` should support Mac only and depend on `vergo_terminal` being selected.

## User Outcome

### Linux

If `vergo_terminal` is selected, Linux users get:

- `zsh`
- `zi`
- `powerlevel10k`
- `zsh-autosuggestions`
- `fast-syntax-highlighting`
- `zsh-completions`
- `eza`
- `zoxide`
- `fzf`
- Meslo Nerd Font files
- managed `~/.zshrc`
- managed `~/.zshenv`
- managed `~/.p10k.zsh`
- optional integrations preserved when present, such as `bun`, `nvm`, `opencode`, Android SDK paths, and `openclaw` completions

Linux users should not receive WezTerm or the macOS window-manager stack in the first clean implementation.

### Mac

If `vergo_terminal` is selected, Mac users get everything above plus:

- `wezterm`
- managed `~/.wezterm.lua`

If `vergo_macos_wm` is also selected, Mac users additionally get:

- `Aerospace`
- `SketchyBar`
- `JankyBorders`
- bundled config files under `~/.config`
- login item registration for Aerospace
- first-run guidance for Accessibility permissions

## Non-Goals

- Do not make VErgo part of Rakkib's always-installed core.
- Do not model VErgo as a Docker service.
- Do not keep the current remote `curl` installer path inside Rakkib execution.
- Do not copy over personal hardcoded assumptions such as `~/MyProjects/agenting/browser-agent/stream.html`.
- Do not expand Linux support beyond Ubuntu-style `apt` in the first pass.

## Design Principles

1. Keep VErgo opt-in.
2. Use repo-local files instead of downloading raw files from GitHub during install.
3. Preserve Rakkib idempotency rules.
4. Back up user-owned dotfiles before replacing or managing them.
5. Keep platform-specific behavior explicit.
6. Minimize surprise on headless servers and non-desktop installs.

## Clean Architecture

### 1. Treat VErgo as a Host Addon

Add a host-addon concept rather than forcing VErgo into `registry.yaml`'s service catalog.

Recommended state shape:

```yaml
host_addons:
  - vergo_terminal
  - vergo_macos_wm
```

Alternative if Rakkib wants to avoid a new top-level state key:

```yaml
selected_host_features:
  - vergo_terminal
  - vergo_macos_wm
```

The first option is cleaner because it distinguishes host customization from server services.

### 2. Split Execution from Current Scripts

Do not shell out to `VErgo/terminal.sh` or `VErgo/aerospace.sh` from Rakkib.

Instead, port their logic into Rakkib step instructions so the agent can:

- detect platform
- install only the required packages
- render repo-local files
- preserve existing user files with backups
- verify each outcome explicitly

This keeps the implementation consistent with `AGENT_PROTOCOL.md` and avoids a second installer model inside the repo.

### 3. Keep Files Repo-Local

Use the existing VErgo files as source assets, but install them from the local checkout.

Primary file sources:

- `VErgo/templates/zshrc.mac.zsh`
- `VErgo/templates/zshrc.ubuntu.zsh`
- `VErgo/templates/zshenv.mac.zsh`
- `VErgo/templates/zshenv.ubuntu.zsh`
- `VErgo/files/.p10k.zsh`
- `VErgo/files/.wezterm.lua`
- `VErgo/files/.config/aerospace/`
- `VErgo/files/.config/sketchybar/`
- `VErgo/files/.config/borders/`

## Required Refactors Before Integration

### 1. Remove Personal Assumptions from Shell Templates

Refactor `VErgo/templates/zshrc.mac.zsh` to remove or gate:

- `~/MyProjects/agenting/browser-agent/stream.html`
- the custom `agent-browser` wrapper behavior
- any alias or behavior that only makes sense on one specific personal workstation

Keep only portable behavior that is safe to install on arbitrary machines.

### 2. Decide Whether `agent-browser` Support Belongs at All

Recommended first-pass decision:

- keep `openclaw` shell completion support
- keep generic `command -v`-guarded optional integrations
- drop the bespoke `agent-browser` wrapper from the clean integration

If desired later, reintroduce it as a separate optional shell feature.

### 3. Fix Naming Drift

Current files still reference `power10k` in variable names and publishing notes.

Normalize language in the integrated implementation to `VErgo` so the Rakkib-facing feature is conceptually consistent.

## Rakkib Changes

### 1. Questions

Add a host-addon section to the interview after service selection.

Recommended placement:

- extend `questions/03-services.md` with a second checklist for host addons
- or add a new `questions/03b-host-addons.md`

Recommended menu:

```text
Optional Host Addons:
  [ ] 1  VErgo Terminal     - shell, prompt, CLI UX
  [ ] 2  VErgo macOS WM     - Aerospace, SketchyBar, Borders (Mac only)
```

Rules:

- show `VErgo macOS WM` only on Mac
- if selected, auto-require `VErgo Terminal`
- clearly warn that this modifies the admin user's dotfiles
- clearly warn that the macOS WM addon is desktop-oriented, not server-oriented

### 2. State

Record:

```yaml
host_addons:
  - vergo_terminal
  - vergo_macos_wm
```

Derived values to record if needed:

```yaml
vergo:
  backup_dir: ~/.backup-vergo/<timestamp>
```

The timestamp itself can still be determined at execution time, but the naming convention should be documented and stable.

### 3. Templates and Static Assets

Add a Rakkib-managed area for VErgo assets.

Recommended structure:

- `templates/vergo/zshrc.mac.zsh.tmpl`
- `templates/vergo/zshrc.ubuntu.zsh.tmpl`
- `templates/vergo/zshenv.mac.zsh.tmpl`
- `templates/vergo/zshenv.ubuntu.zsh.tmpl`
- `templates/vergo/wezterm.lua.tmpl` or static file if no placeholders are needed
- `files/vergo/.p10k.zsh`
- `files/vergo/.config/aerospace/...`
- `files/vergo/.config/sketchybar/...`
- `files/vergo/.config/borders/...`

Even if most files are static today, move them into Rakkib's managed layout so future customization remains easy.

### 4. Steps

Add a dedicated post-confirmation step for host personalization.

Recommended new step:

- `steps/72-host-customization.md`

Suggested execution order:

1. `steps/70-host-agents.md`
2. `steps/72-host-customization.md`
3. `steps/80-backups.md`

This keeps host-level user tooling close to other non-container host work.

## Step Design

### `steps/72-host-customization.md`

This step should only run if `host_addons` is non-empty.

#### Linux actions for `vergo_terminal`

1. Ensure `sudo` is available for package installation when needed.
2. Ensure `apt-get` exists.
3. Install required packages:
   - `zsh`
   - `git`
   - `curl`
   - `eza`
   - `zoxide`
   - `fzf`
4. Install or update `zi` into `~/.zi/bin`.
5. Install Meslo Nerd Font files into `~/.local/share/fonts`.
6. Back up existing user files before replacing them:
   - `~/.zshrc`
   - `~/.zshenv`
   - `~/.p10k.zsh`
7. Render or copy the Ubuntu shell files into place.
8. Warn if the current login shell is not `zsh` and provide `chsh -s` guidance.
9. Do not force a shell change automatically in the first pass.

#### Mac actions for `vergo_terminal`

1. Ensure Homebrew is available.
2. Install required packages:
   - `zsh`
   - `git`
   - `curl`
   - `eza`
   - `zoxide`
   - `fzf`
   - `wezterm`
3. Install or update `zi` into `~/.zi/bin`.
4. Install Meslo Nerd Font files into `~/Library/Fonts`.
5. Back up existing user files before replacing them:
   - `~/.zshrc`
   - `~/.zshenv`
   - `~/.p10k.zsh`
   - `~/.wezterm.lua`
6. Render or copy the macOS shell files into place.
7. Install `~/.wezterm.lua`.
8. Warn if the current login shell is not `zsh` and provide `chsh -s` guidance.

#### Mac actions for `vergo_macos_wm`

1. Ensure Homebrew is available.
2. Install packages:
   - `nikitabobko/tap/aerospace`
   - `FelixKratz/formulae/sketchybar`
   - `FelixKratz/formulae/borders`
   - `font-sf-pro`
   - `font-jetbrains-mono-nerd-font`
3. Back up existing config directories before replacing them:
   - `~/.config/aerospace`
   - `~/.config/sketchybar`
   - `~/.config/borders`
4. Copy the managed config tree into `~/.config`.
5. Set executable bits on the expected scripts.
6. Register Aerospace as a login item.
7. Do not auto-launch Aerospace during install.
8. Print post-install guidance about logout/login and Accessibility permissions.

## Idempotency Rules

The clean implementation must define explicit VErgo-specific idempotency behavior.

### Backups

- Use a timestamped backup directory such as `~/.backup-vergo/<timestamp>/`.
- If a file is already managed and unchanged from the previous Rakkib-managed version, do not create duplicate backups on every rerun unless the file content is about to change.

### Managed Files

Track these as Rakkib-managed targets:

- `~/.zshrc`
- `~/.zshenv`
- `~/.p10k.zsh`
- `~/.wezterm.lua`
- `~/.config/aerospace/...`
- `~/.config/sketchybar/...`
- `~/.config/borders/...`

Recommended approach:

- compare candidate content before replacing files
- only write when content differs
- preserve permissions where appropriate

### Zi Install

- if `~/.zi/bin/.git` exists, update with `git pull --ff-only`
- otherwise clone it fresh

### Fonts

- re-download only when missing or when an explicit refresh is requested
- run `fc-cache` on Linux when available

## Verification

Add explicit verification items to `steps/72-host-customization.md` and final verification to `steps/90-verify.md`.

### Verify `vergo_terminal`

- `command -v zsh`
- `test -f ~/.zshrc`
- `test -f ~/.zshenv`
- `test -f ~/.p10k.zsh`
- `test -d ~/.zi/bin`
- `zsh -i -c exit`

Mac only:

- `test -f ~/.wezterm.lua`
- `test -f "$HOME/Library/Fonts/MesloLGS NF Regular.ttf"`

Linux only:

- `test -f "$HOME/.local/share/fonts/MesloLGS NF Regular.ttf"`

### Verify `vergo_macos_wm`

- `test -f ~/.config/aerospace/aerospace.toml`
- `test -f ~/.config/sketchybar/sketchybarrc`
- `test -f ~/.config/borders/bordersrc`
- `brew list --cask | grep aerospace`
- `brew list | grep sketchybar`
- `brew list | grep borders`

If practical, also verify the login item registration in a non-fragile way, but this can remain best-effort if macOS automation is inconsistent.

## Documentation Changes

Update these docs:

1. `README.md`
2. `AGENT_PROTOCOL.md`
3. any relevant question files
4. any host-addon documentation section that explains the difference between server services and user-environment addons

README changes should explain:

- VErgo Terminal is optional
- it modifies the admin user's shell environment
- macOS WM is separate and Mac-only
- this feature is best suited for developer-owned machines, not minimal headless hosts

## Implementation Phases

### Phase 1: Normalize VErgo Assets

1. Remove personal hardcoded behavior from shell templates.
2. Decide which optional shell integrations remain.
3. Rename or document `power10k` references so the feature reads as `VErgo` in Rakkib.

### Phase 2: Add Interview and State Support

1. Add host-addon selection to the interview flow.
2. Record the chosen addon values in `.fss-state.yaml`.
3. Validate Mac-only selection rules for `vergo_macos_wm`.

### Phase 3: Add Managed Assets

1. Move or copy the clean VErgo templates into Rakkib-managed template and file paths.
2. Define any placeholders needed.
3. Keep the first version mostly static unless customization is required.

### Phase 4: Add Execution Step

1. Create `steps/72-host-customization.md`.
2. Add platform-specific package install logic.
3. Add repo-local render/copy logic.
4. Add backup behavior.
5. Add verify blocks.

### Phase 5: Integrate Final Verification

1. Extend `steps/90-verify.md` for selected host addons.
2. Ensure final success criteria include VErgo only when selected.

### Phase 6: Test Rerun Behavior

1. Test on Ubuntu with `vergo_terminal` selected.
2. Test on Mac with `vergo_terminal` selected.
3. Test on Mac with both addons selected.
4. Re-run the installer and confirm no duplicate or destructive behavior.

## Acceptance Criteria

The clean implementation is complete when:

1. Users can opt into VErgo during the Rakkib interview.
2. Linux and Mac terminal setup is installed without using the remote VErgo bootstrap scripts.
3. The macOS WM addon is available only on Mac.
4. Existing user files are backed up before replacement.
5. Rerunning Rakkib does not duplicate or unnecessarily rewrite managed VErgo assets.
6. Final verify passes for selected addons.
7. No personal-path assumptions remain in installed shell files.

## Recommended First Slice

If implementation should be staged, build in this order:

1. `vergo_terminal` on Linux and Mac
2. final verification for terminal setup
3. `vergo_macos_wm`

This yields useful user value early while keeping the more desktop-specific Mac work isolated.

## Risks

1. Dotfile replacement is inherently higher-risk than container setup.
2. Homebrew-based installs may be slower and less predictable than Dockerized services.
3. Linux desktop expectations can drift if users assume WezTerm or WM features also apply there.
4. macOS login-item registration may be slightly brittle across OS versions.

## Recommendation

Proceed with `vergo_terminal` first and treat it as the main clean integration target.

Treat `vergo_macos_wm` as a second-phase addon after the portable shell experience is working cleanly under Rakkib's stateful, idempotent installer model.
