# Enable Powerlevel10k instant prompt. Keep near the top of ~/.zshrc.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Disable the gitstatus background worker when there's no job control
# (e.g., tools that open an interactive shell without a TTY).
if [[ -o interactive ]] && ! [[ -t 0 && -t 1 ]]; then
  typeset -g POWERLEVEL9K_DISABLE_GITSTATUS=true
fi

typeset -A ZI
ZI[BIN_DIR]="${HOME}/.zi/bin"
source "${ZI[BIN_DIR]}/zi.zsh"

# Keep the plugin manager available after zoxide takes over `zi`.
functions[ziplugin]=$functions[zi]

if [[ -o interactive ]]; then
  [[ -d "$HOME/.docker/completions" ]] && fpath=("$HOME/.docker/completions" $fpath)

  # Completions must load before compinit runs.
  ziplugin light zsh-users/zsh-completions

  autoload -Uz compinit
  # Rebuild dump at most once per 24h for faster interactive startup.
  _zcompdump="${XDG_CACHE_HOME:-$HOME/.cache}/zcompdump"
  if [[ -n "$_zcompdump"(#qN.mh+24) ]]; then
    compinit -d "$_zcompdump"
  else
    compinit -C -d "$_zcompdump"
  fi
  unset _zcompdump

  autoload -Uz _zi
  (( ${+_comps} )) && _comps[ziplugin]=_zi

  ziplugin light romkatv/powerlevel10k
  ziplugin light zsh-users/zsh-autosuggestions

  alias ls="eza --icons=always"
  eval "$(zoxide init zsh)"
  alias cd="z"
fi

alias pip="python3 -m pip"
alias pip3="python3 -m pip"

export NVM_DIR="$HOME/.nvm"
if [[ -o interactive ]]; then
  [[ -s "$NVM_DIR/nvm.sh" ]]          && source "$NVM_DIR/nvm.sh"
  [[ -s "$NVM_DIR/bash_completion" ]] && source "$NVM_DIR/bash_completion"

  [[ -s "$HOME/.bun/_bun" ]] && source "$HOME/.bun/_bun"

  [[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
fi

if [[ -o interactive ]] && command -v openclaw >/dev/null 2>&1; then
  source <(openclaw completion --shell zsh 2>/dev/null)
fi

# Keep syntax highlighting last so it sees the final widget state.
if [[ -o interactive ]]; then
  ziplugin light zdharma-continuum/fast-syntax-highlighting
fi
