# Sourced by ALL zsh invocations (login, interactive, scripts).
# Keep this file minimal and side-effect free — PATH and exports only.

# Deduplicate PATH so nested shells don't grow it.
typeset -U path PATH

[[ -d "$HOME/.local/bin"                   ]] && path=("$HOME/.local/bin"                   $path)
[[ -d "$HOME/.bun/bin"                     ]] && path=("$HOME/.bun/bin"                     $path)
[[ -d "$HOME/.opencode/bin"                ]] && path=("$HOME/.opencode/bin"                $path)
[[ -d "$HOME/.antigravity/antigravity/bin" ]] && path=("$HOME/.antigravity/antigravity/bin" $path)

# Android SDK (Ubuntu convention: ~/Android/Sdk or ~/Android/sdk).
for _sdk in "$HOME/Android/Sdk" "$HOME/Android/sdk"; do
  if [[ -d "$_sdk" ]]; then
    export ANDROID_SDK_ROOT="$_sdk"
    export ANDROID_HOME="$_sdk"
    path=("$_sdk/cmdline-tools/latest/bin" "$_sdk/platform-tools" "$_sdk/emulator" $path)
    break
  fi
done
unset _sdk

export BUN_INSTALL="$HOME/.bun"
