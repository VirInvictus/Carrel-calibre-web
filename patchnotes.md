# Patchnotes (Carrel-calibre-web)

## cquarry 1.8 sync + editable install (2026-08-26 → 0.6.28, 2026-08-30)

- **Deployment venv reinstalled EDITABLE from `~/.gitrepos/cquarry`** (Carrel
  spec §8.2's documented contract). The stale non-editable cquarry 1.1.1 in
  site-packages predated the branch's 1.3 API calls — the running instance
  silently degraded page_count to None. Installed == repo now, and it cannot
  drift again.
- **`cps/library_cache.py`'s UUID read adopts cquarry's URI contract.** The
  "deliberately does NOT go through cquarry" note was a stale-install
  artifact, not architecture: the Phase 4 venv predated `get_library_uuid()`.
  The read stays a single one-query mode=ro connection (a full CalibreDB
  lifecycle would regress the per-cache-hit cost the module exists to keep
  cheap), but the URI now comes from cquarry's `db_uri_ro()` — whose
  percent-encoding the old bare f-string was missing, a latent break on
  library paths containing `?` or `#`. Analytics adoption stays deferred to
  cquarry's Phase 7 (don't patch the fork twice).
- **Version 0.6.28** (fork-side bump in `cps/constants.py`), which also
  leapfrogs upstream's in-flight 0.6.27b numbering before the next deliberate
  rebase. README's test count corrected to the real 35.

## cquarry 1.3 adoption (2026-08-26)

- **Native page counts on the detail page (`cps/page_count.py`).** Calibre
  maintains per-book page counts in its own `books_pages_link` table (the
  CountPages integration); cquarry 1.3 reads that table natively with the
  `#pages` custom column kept as an older-schema fallback. A new Jinja global
  `carrel_page_count(book_id)` follows the reader_state pattern — answers or
  says None, never 500s — and detail.html renders a "Pages" line only when the
  library actually knows.
- **Library-identity cache invalidation (`cps/library_cache.py`).** The six
  LibraryCache surfaces (wings, categories, search, series, statistics,
  palette — plus reader state and page count) now key on metadata.db's mtime
  AND the library's identity UUID from `library_id`. An mtime alone cannot
  tell a restored *copy* from the original (`cp -p` reproduces timestamps);
  after a move/restore the bundled copy rebuilds instead of serving cached
  state. Identity reads use a bare mode=ro SELECT so validation stays cheap;
  schemas predating `library_id` degrade to mtime-only, exactly as before.
- **Tests:** fixture gains native page rows; new coverage for the detail-page
  "Pages" line, absent-count degradation, and equal-mtime/identity-swap cache
  rebuilds. Suite: 82 tests green.

## cquarry 1.1 adoption (2026-08-25)

Deepens the fork's use of the shared engine. No upstream file gains new
behaviour; everything lives in Carrel-owned modules.

- **Saved Searches sidebar (`cps/saved_searches.py`).** Calibre's named
  searches (`preferences.saved_searches`) become browse sections at
  `/saved/<name>`, resolved through cquarry 1.1's `search:"Name"`
  interpolation \u2014 cycle detection, strict errors on unknown names, and exact
  agreement with whatever the search bar evaluates.
- **Calibre-exact wing layout (`cps/wings.py`).** The sidebar now follows
  Calibre's stored tab order and hidden list via `get_vl_ui_state()`
  (`virt_libs_order` / `virt_libs_hidden`); unknown wings fall back to
  alphabetical after the ordered ones, hidden ones drop out entirely.
- **Reader state on the detail page (`cps/reader_state.py`).** A
  `carrel_reader_state(entry.id)` template global exposes the latest per-device
  reading progress (`last_read_positions`, most recent `epoch_time` wins) and
  the book's highlight count (`annotations`); absent data renders nothing.
- **Fixture/tests.** The fixture library gains saved searches, a hidden wing,
  stored tab order, annotations and two devices' positions; ten new tests pin
  the sidebar counts, exact filtering, cache invalidation, engine/route
  agreement, hidden-wing 404, tab order, and reader-state rendering.
- **Requires cquarry >= 1.1** (CI already installs from the standalone repo's
  main branch).
- **Fix:** `last_read_positions` rows follow Calibre's real schema
  (`format`/`user`/`device`/`cfi`/`epoch`/`pos_frac`; no `user_type`, the time
  column is `epoch`). Reader-state picks the latest device by `epoch`.
- **Fix:** saved-search pages are excluded from index.html's sort header (the
  documented BuildError hazard), and empty-result searches render an empty grid
  instead of erroring.
- **Tests:** fixture aligns with the dumped real schema for annotations and
  reading positions; suite is stable across repeated runs.
