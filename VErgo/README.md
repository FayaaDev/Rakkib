# VErgo

Fayaa's portable terminal bootstrap for macOS and Ubuntu.

## One-line install

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/FayaaDev/VErgo/main/terminal.sh)"
```

## What it installs

- `zsh`
- `zi`
- `powerlevel10k`
- `zsh-autosuggestions`
- `fast-syntax-highlighting`
- `zsh-completions`
- `eza`
- `zoxide`
- `fzf`
- `wezterm` (macOS only — cask)
- your exact `~/.p10k.zsh`
- your exact `~/.wezterm.lua`
- a portable `~/.zshrc` for macOS or Ubuntu
- Meslo Nerd Font files

## Behavior

- Supports macOS and Ubuntu-style Linux systems with `apt`
- Backs up existing `~/.zshrc` and `~/.p10k.zsh` into `~/.backup-power10k/<timestamp>/`
- Preserves optional integrations if they already exist on the machine:
  - `OpenClaw`
  - `bun`
  - `nvm`
  - `opencode`
  - Docker completions
  - Android SDK paths

## After install

```bash
exec zsh
```

If the prompt icons do not render correctly, set your terminal font to `MesloLGS NF`.

## macOS window manager (optional)

On top of the base terminal setup, a second installer ships Fayaa's tiling WM stack:
[aerospace](https://github.com/nikitabobko/AeroSpace) + [sketchybar](https://github.com/FelixKratz/SketchyBar) + [JankyBorders](https://github.com/FelixKratz/JankyBorders), themed with tokyonight.

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/FayaaDev/VErgo/main/aerospace.sh)"
```

Installs: `aerospace` (cask), `sketchybar`, `borders`, `font-sf-pro`, `font-jetbrains-mono-nerd-font`.

Registers Aerospace.app as a login item but does **not** launch it during install — log out and back in, or run `open -a Aerospace` to start immediately. On first launch macOS will prompt for Accessibility permission (required for aerospace to manage windows).

## Repository layout

- `terminal.sh`: terminal bootstrap installer (zsh, zi, powerlevel10k, wezterm, fonts)
- `aerospace.sh`: macOS window manager installer (aerospace, sketchybar, borders)
- `files/.p10k.zsh`: exact prompt config
- `files/.wezterm.lua`: exact WezTerm config
- `files/.config/aerospace/`: aerospace tiling WM config
- `files/.config/sketchybar/`: sketchybar status bar config (items, plugins, tokyonight theme)
- `files/.config/borders/`: JankyBorders window border config
- `templates/zshrc.mac.zsh`: macOS shell template
- `templates/zshrc.ubuntu.zsh`: Ubuntu shell template

## Publishing

The one-line install command expects these files to be pushed to the `main` branch of `FayaaDev/power10k`.
