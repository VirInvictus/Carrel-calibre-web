# CLAUDE.md (Carrel-calibre-web)

Fork of janeczku/calibre-web carrying Brandon's Kanagawa Dragon theme and
library-specific adaptations. **The contract lives in the companion repo:**
`~/.gitrepos/Carrel/` (`spec.md`, `roadmap.md`, `CLAUDE.md`).
Read those before changing anything here.

The short version of the rules:

- Work only on the `smallscope` branch (cut from tag `0.6.26`). `master`
  tracks upstream; never commit to it.
- `metadata.db` is attached read-only by design and must stay that way.
  No code path may write the library, and no test may touch
  `~/docs/Calibre Library/`. Tests use the fixture DB in `tests/`.
- `cps/static/css/kanagawa-dragon.css` is VENDORED from
  `Carrel/theme/` via `just sync-theme`; edit it there, not here.
- Keep the diff rebase-friendly: disable routes rather than delete files;
  put new code in new modules (`cps/wings.py`).
- Upstream code style applies in upstream files (this is GPL-3.0 third-party
  code; match what's there, not the personal conventions).
- A formatter hook reformats Python touched via Claude's Edit/Write tools,
  which churns whole upstream files and poisons rebases. Patch upstream
  `.py` files via shell (python heredoc) instead; templates, CSS, and our
  own new modules (`cps/smallscope.py`, `cps/wings.py`, `tests/`) are fine
  to edit normally.

Run from source (the venv holds the dependencies; the calibreweb wheel is
uninstalled): `CALIBRE_DBPATH=~/.calibre-web ~/calibre-web-env/bin/python cps.py`,
or `just serve` from the kanagawa repo.
Tests: `~/calibre-web-env/bin/python -m unittest discover -s tests`.
