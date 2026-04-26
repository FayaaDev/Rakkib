# Sourced by ALL zsh invocations (login, interactive, scripts).
# Keep this file minimal and side-effect free — PATH and exports only.

# Deduplicate PATH so nested shells don't grow it.
typeset -U path PATH

[[ -d "$HOME/.local/bin"                   ]] && path=("$HOME/.local/bin"                   $path)
[[ -d "$HOME/.bun/bin"                     ]] && path=("$HOME/.bun/bin"                     $path)
[[ -d "$HOME/.opencode/bin"                ]] && path=("$HOME/.opencode/bin"                $path)
[[ -d "$HOME/.antigravity/antigravity/bin" ]] && path=("$HOME/.antigravity/antigravity/bin" $path)

# Android SDK (macOS convention: ~/Library/Android/sdk).
if [[ -d "$HOME/Library/Android/sdk" ]]; then
  export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
  export ANDROID_HOME="$ANDROID_SDK_ROOT"
  path=("$ANDROID_SDK_ROOT/cmdline-tools/latest/bin" "$ANDROID_SDK_ROOT/platform-tools" "$ANDROID_SDK_ROOT/emulator" $path)
fi

export BUN_INSTALL="$HOME/.bun"
