# Rakkib - runtime branch

This branch is the slim install snapshot used by the curl-pipe installer.
It contains only the files needed to run `rakkib` on a target host:
`install.sh`, `pyproject.toml`, `.gitignore`, `src/rakkib/**`.

For development, issues, docs, and tests, see the `main` branch:
https://github.com/FayaaDev/Rakkib/tree/main

To sync this branch from `main` after changes land there:
    git fetch origin
    git switch runtime
    git checkout main -- install.sh pyproject.toml .gitignore src/
    git commit -m "sync from main@<sha>"
    git push
