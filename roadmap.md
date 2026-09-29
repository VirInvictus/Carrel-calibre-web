# Roadmap (Carrel-calibre-web)

Created 2026-09-29 during the ecosystem parity scoping: this fork's live queue
previously lived in the companion repo's roadmap fork blocks (Carrel roadmap.md,
Waves 17-18) plus the fork's patchnotes and project.done; it now lives here. The
contract still lives in `~/.gitrepos/Carrel/` (spec.md authoritative: §6.3 the
cquarry data layer, §8.5 reader state, §11 single-user, §12.3 the stats boundary,
§13 search parity); this file records open work only. Fork point 0.6.26; branch
`smallscope`; fork version 0.6.42 (`cps/constants.py`); suite 86 tests.

**Parity lane (2026-09-29):** the web reading room, against Calibre's own Content
Server (`src/calibre/srv` in the reference clone). The read paths are
cquarry-backed or sealed; everything the upstream server offers beyond this fork's
surface (writes, conversion-on-download, reading-position writes, user management,
kobo sync) is declined by contract, not missing. The declines section below is
this repo's D-lane record for the parity ledger (cquarry roadmap.md, "The parity
program").

## Open work

- [ ] **Retire the preserve_order re-sort shim with `list_books(sort="ids")`**
      (`cps/quarry_grid.py:604` signature, `:628-630` re-sort; live callers
      `web.py:532` render_hot_books and `web.py:568` render_downloaded_books).
      cquarry 1.21.0 built the mode for exactly this (its API.md names it as the
      shim's retirement); fork CI already pins cquarry v1.21.0 (`ci.yml`), so this
      is adoption only, then the shim and its parameter die. Size S.
- [ ] **Swap the two remaining fork-owned raw reads of metadata.db to
      `load_custom_column()`**: `reading_shelf.py:28-62` (the custom_columns lookup
      plus the two-branch normalized/direct query; `load_custom_column("reading_status")`
      plus `get_all_books()` rows retire the branch logic with it) and
      `stats.py:119-144` `_custom_column_breakdown` (same shape). stats.py's other
      raw SQL is core-table surface under spec 12.3 and stays. Size S.
- [ ] **serve_book and cover resolution still stream through the ORM**
      (`web.py:1564-1567` `get_book`/`get_book_format`; `web.py:1526-1538`
      `get_cover` -> `get_book_cover`): the last large ORM data paths (Carrel
      roadmap.md:843-846). Functional today; the swap is the sealing lane's tail.
      Size M.
- [ ] **`/basic_book` detail is still ORM** (`basic.py:81-84`
      `get_book_read_archived`): low priority by the standing ruling; moves only
      when it is in the way of something. Size XS.
- [ ] **Upstream security cherry-picks (next fork lane; parked, not declined)**:
      8-9 substantive upstream fixes on live fork surfaces (SQLI via dbpath; the
      /show/ serve_book bypass; XXE in epub parsing; the debug_info credential
      leak; the non-admin stacktrace leak; CSP entropy; comment-column escaping;
      the download-path staged-tmp/cover-sibling pair). Recorded in both
      project.done files; re-check at the next upstream tag. Size M.
- [ ] **Helper adoptions when cquarry Phase 16 promotes them** (the Cross-Repo
      Implementation Rule's fork half): the ordered-VL-names helper (retires
      `cps/wings.py:33-47`), the unpiped-author display helper (retires the nine
      `replace("|", ",")` sites), the tag-membership id-set rollup (retires
      `cps/categories.py:29-52`), and the **Open Library ISBN switch**: `_ID_URLS`
      at `quarry_grid.py:581` moves WorldCat -> `openlibrary.org/isbn/` per
      Brandon's 2026-09-29 canonical call. Size XS each.
- [ ] **cquarry residue trio pull-hook**: `get_book_by_uuid`, the entity-to-ids
      resolver, and the bulk formats map are ungated in cquarry's Phase 14; this
      fork adopts whichever a surface needs (the Calibre-Companion endpoint wants
      the first; the serve_book/cover swap could use the third). No adoption is
      committed by itself; the endpoint stays waived (below).

## Declined (the D-lane record; reversal needs a new recorded decision)

- Read-only by construction (Carrel spec 1.4/7/14): no code path writes the
  library; metadata.db attaches `?mode=ro` and the tests pin it.
- Reading-status writes waived permanently (Carrel spec 5.1/5.2; the fork
  patchnotes waiver line): status is Brandon-curated and read-only from the web.
- No conversion-on-download (the send/convert chain was stubbed at 0.6.40); held
  formats only.
- No reading-position write path (Carrel spec 8.5): devices write positions
  through Calibre desktop; the fork only consumes `last_read_positions`.
- No user management, no web metadata editing, no shelves, no registration, no
  multi-library, no kobo sync (config-off and sealed; upstream's own server ships
  no kobo endpoint either).
- The Calibre-Companion JSON endpoint and the OPDS custom-column content block:
  waived 2026-09-11 (no consumer; KOReader consumes the feeds as they ship).

## Traps and standing notes

- Patch upstream `.py` via shell heredoc (the rebase-cleanliness rule in
  CLAUDE.md); templates, CSS, and our own new modules edit normally.
- Entity URLs are `/<data>/<sort_param>/<id>` while overview pages are bare; a
  missing id silently defaults book_id to 1 (`web.py:939-957`).
- The cquarry three-version skew (venv dist-info 1.8.0, editable tree 1.23.2, CI
  pin v1.21.0) is recorded in Carrel's roadmap with its fix shapes.
- The stats-metrics tripwire lives in Carrel spec 12.3 (a fourth library-metrics
  consumer triggers the headless-layer conversation).
- The 1.0.0 gates are the five sign-off boxes in Carrel's roadmap; this file adds
  none.
