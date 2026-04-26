#!/usr/bin/env bash

set -euo pipefail

OWNER="${POWER10K_REPO_OWNER:-FayaaDev}"
REPO="${POWER10K_REPO_NAME:-power10k}"
BRANCH="${POWER10K_REPO_BRANCH:-main}"
RAW_BASE="${POWER10K_RAW_BASE:-https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}}"

log() {
  printf '[aerospace] %s\n' "$*"
}

warn() {
  printf '[aerospace] WARNING: %s\n' "$*" >&2
}

die() {
  printf '[aerospace] ERROR: %s\n' "$*" >&2
  exit 1
}

download_to() {
  local url="$1"
  local path="$2"
  curl -fsSL "$url" -o "$path"
}

brew_cmd() {
  if command -v brew >/dev/null 2>&1; then
    command -v brew
  elif [ -x /opt/homebrew/bin/brew ]; then
    printf '/opt/homebrew/bin/brew\n'
  elif [ -x /usr/local/bin/brew ]; then
    printf '/usr/local/bin/brew\n'
  else
    return 1
  fi
}

ensure_homebrew() {
  if brew_cmd >/dev/null 2>&1; then
    return
  fi

  log 'Installing Homebrew'
  NONINTERACTIVE=1 bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

backup_dir_if_exists() {
  local path="$1"
  if [ -e "$path" ]; then
    cp -a "$path" "$BACKUP_DIR/$(basename "$path")"
  fi
}

# macOS only
if [ "$(uname -s)" != 'Darwin' ]; then
  die 'This installer is macOS-only (aerospace, sketchybar, and borders are macOS applications).'
fi

ensure_homebrew

brew="$(brew_cmd)"

log 'Installing packages with Homebrew'
"$brew" install --cask nikitabobko/tap/aerospace
"$brew" install FelixKratz/formulae/sketchybar FelixKratz/formulae/borders
"$brew" install --cask font-sf-pro font-jetbrains-mono-nerd-font

BACKUP_DIR="$HOME/.backup-power10k/$(date +%Y%m%d%H%M%S)"
mkdir -p "$BACKUP_DIR"

log 'Backing up existing window-manager configs'
backup_dir_if_exists "$HOME/.config/aerospace"
backup_dir_if_exists "$HOME/.config/sketchybar"
backup_dir_if_exists "$HOME/.config/borders"

log 'Downloading configs'

# Config files relative to files/.config/ in the repo
config_files=(
  'aerospace/aerospace.toml'
  'borders/bordersrc'
  'sketchybar/sketchybarrc'
  'sketchybar/environment'
  'sketchybar/items/aerospace'
  'sketchybar/items/clock'
  'sketchybar/items/front_app'
  'sketchybar/items/spacer'
  'sketchybar/plugins/aerospace'
  'sketchybar/plugins/clock'
  'sketchybar/plugins/front_app'
  'sketchybar/themes/tokyonight'
)

for rel in "${config_files[@]}"; do
  dest="$HOME/.config/$rel"
  mkdir -p "$(dirname "$dest")"
  download_to "$RAW_BASE/files/.config/$rel" "$dest"
done

log 'Setting executable bits'
chmod +x \
  "$HOME/.config/sketchybar/sketchybarrc" \
  "$HOME/.config/sketchybar/plugins/aerospace" \
  "$HOME/.config/sketchybar/plugins/clock" \
  "$HOME/.config/sketchybar/plugins/front_app" \
  "$HOME/.config/borders/bordersrc"

log 'Registering Aerospace as a login item'
osascript -e 'tell application "System Events" to make login item at end with properties {path:"/Applications/Aerospace.app", hidden:false}' \
  >/dev/null 2>&1 \
  || warn 'Could not register Aerospace.app as a login item — add it manually via System Settings → General → Login Items.'

log "Backups saved to $BACKUP_DIR"
log 'Install complete'
log 'Next steps:'
log '1. Log out and back in to activate Aerospace (it will start sketchybar and borders automatically)'
log '   — or run: open -a Aerospace'
log '2. On first launch, macOS will prompt for Accessibility permission — grant it so Aerospace can manage windows'
