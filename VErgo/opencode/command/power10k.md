---
description: Install Fayaa's portable power10k terminal setup on this device
tools:
  bash: true
---

Before running anything, tell the user:
- This installer supports macOS and Ubuntu.
- It backs up `~/.zshrc` and `~/.p10k.zsh` before replacing them.
- The exact Powerlevel10k look depends on setting the terminal font to `MesloLGS NF` after install.

Then run:

!`bash -c "$(curl -fsSL https://raw.githubusercontent.com/FayaaDev/power10k/main/terminal.sh)"`

After it completes:
- Summarize what was installed.
- Mention the usual shell restart step: `exec zsh`.
- Remind the user to set their terminal font to `MesloLGS NF` if icons or prompt glyphs look wrong.
