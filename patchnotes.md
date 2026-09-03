# Patchnotes (Carrel-calibre-web)
## Phase 7: the browse grids join the swap (2026-09-03, 0.6.33)

- **Every entity browse grid now pages through cquarry.** Author,
  publisher, series, category, language, ratings, formats, rated, and the
  newest default grid resolve their book-id sets rows-side
  (`quarry_grid.ids_for_entity` / `ids_missing` / `ids_with` over the
  cached rows — entity id → name/value → row match; no per-entity
  queries, no new cquarry API needed) and page via `quarry_grid.grid`
  with the sort header honored through `SEARCH_SORTS`. None-variants
  (untagged, no publisher, no language, no formats, unrated) are set
  subtractions via `ids_missing`, preserving the `-1` URL semantics.
- **Discover (random) and the degrade path.** Discover samples ids with
  `random.sample` instead of `func.randomblob`; the newest grid degrades
  to an empty page when the library vanishes mid-request, exactly as the
  old `fill_indexpage` path did (the degrade test caught the 500).
- **Two URL-shape fixes the tests caught:** entity ids arrive from URLs
  as strings, so `entity_name`/`ids_for_entity` coerce to int (SQLite
  used to do that coercion silently); and the four swapped return lines
  that still referenced the removed `random` local were fixed.
- **Version 0.6.33.** Suite 102 green. Remaining Phase 7 surface:
  web.py's remaining routes (hot/downloaded/archived stay app-DB-coupled
  for now), opds.py, show_book/read_book detail, helper.py lookups.

## Phase 7 continued: the search results page and /basic join the swap
(2026-09-03, 0.6.32)

- **/search results page through cquarry's list_books.** `render_search_results`
  resolved ids through cquarry's engine but still paged them via the stock ORM
  `fill_indexpage` (with the series join riding along for the authaz/authza
  sorts). The paging now goes through `quarry_grid.grid()`, whose new
  `SEARCH_SORTS` map carries the sort header onto `list_books` keys —
  `authaz` = author_sort, series, series_index ascending (the ORM's exact
  shape, enabled by cquarry 1.11's multi-key sorts), `authza` descending,
  and the title/date/publisher tokens likewise. The route passes the
  RESOLVED sort token (`order[1]`, after the saved view-property
  substitution), not the raw one.
- **/basic searches through the one grammar.** The low-bandwidth fallback
  page was the last holdout of the old ORM search grammar (spec 13); its
  query now resolves through `carrel_search` and pages via `quarry_grid`
  (compact 15-per-page kept via the new grid `per_page` override), and a
  malformed query degrades to an empty result page instead of a 500.
- Requires cquarry 1.11.1 (`2f05b0d`): its `list_books` "sort" key was a
  silent no-op (missing row-key alias) that 1.11.0's tests missed because
  the cache arrives pre-sorted — found by this fork's descending search
  sort, fixed upstream in the same wave.
- Suite 100 → 102 discovered (51 base): the sort-header test now exercises
  the cquarry path (and caught the upstream bug), plus grid/pagination
  unit tests and /basic grammar + degradation coverage.

## Phase 7: the hybrid unwinds (2026-09-03, 0.6.31)

- **Wings, saved searches, and categories page through cquarry now.** The
  three surfaces resolved their book-id sets through cquarry's search
  engine but still paged them through the stock ORM `fill_indexpage` —
  the hybrid the boundary map called out. New `cps/quarry_grid.py`
  finishes the swap: cquarry 1.10's `list_books()` pages the rows, and a
  clean-room adapter builds exactly the attribute surface `index.html`
  renders (`entry.Books.title/series[0].id/ratings[0].rating/authors/
  data`, the `entry[2]` read badge from the read column, and a
  Flask-shaped pagination shim with ellipsis arithmetic). The ORM and
  its query builders are off these pages entirely.
- **The categories rollup too.** `_rollup()`'s tag→book pairs come from
  cquarry's cached rows (every book row carries its tags) instead of an
  ORM session query — same implied-prefix rule.
- **A falsy-empty trap the tests caught**: `grid()` treated an empty
  id-set as "the whole library" (bare `if ids`), which would have made
  the saved search matching nothing render every book — the exact bug
  the "renders not 404s" test guards. `None` means everything; an empty
  set means an empty page, and the distinction is now explicit and
  test-pinned.
- **Version 0.6.31.** Suite 96 → 100 discovered (50 base). Remaining
  Phase 7 surface (web.py, opds.py, search.py results assembly,
  basic.py) stays future work, scoped by the boundary map.

## Phase 7 begins: the data-layer swap's first increments (2026-09-03, 0.6.30)

The NEW-AUDIT Stage 6 boundary map classified every cps/db.py call site;
this release lands the riders and the first two swap increments. The live
swap surface (web.py, opds.py, search.py) remains future work by design.

- **Series awareness reads cquarry now.** `series_info._rebuild()` dropped
  its ORM session query: ids come from `get_entities("series")`, index
  rollups from `get_all_series()`, and gap detection from
  `detect_series_gaps()` as it always has. Same output shape the detail
  page has always consumed (fixture test unchanged and green).
- **Covers resolve through `get_cover_path()`.** The local-disk branch of
  `get_book_cover_internal` no longer hardcodes `cover.jpg`: cquarry
  resolves jpg-primary/png-fallback with existence verification, served
  through the new shared `library_cache.quarry()` (one mtime/UUID-keyed
  CalibreDB for the surfaces that only need a handle). Behavior win: a
  png-only catalogued cover serves its real art instead of degrading to
  the generic. Fixture test pins the png case end to end.
- **Acquisition pace joins /statistics via `cquarry.analytics`.** A new
  "Acquisition pace by year" ledger computed by
  `analytics.addition_timeline()` — the derivation is database-shaped, so
  it lives upstream per the frontend-only split. (The first wiring called
  it with the wrong shape and the degrade-to-empty path masked it; the new
  test asserts real fixture data so that class of bug cannot hide again.)
- **Version 0.6.30.** Suite 92 → 96 discovered (48 base), green from the
  deployment venv.

## Phase 12 sweep + the two verdicts (2026-09-02, 0.6.29)

- **Falsy series index 0.** "Book 0" is a real place in a series and kept
  vanishing: `carrel_series` coerced with a truthiness check and the detail
  template gated the badge on `{% if cs.index %}`, so an index of 0/0.0
  rendered as no number at all. The coercion now tests `is not None` and the
  template gates on `is not none`. Fixture-backed test pins #0 as an int and
  the fractional 7.5 passthrough.
- **Route guards are case-normalized.** `seal_browse_surfaces` lowercases
  both sides before matching, so `/HOT` and `/Discover` 404 exactly like
  their lowercase forms (a capitalized bypass was not a feature). Test pins
  the capitalized shapes.
- **The palette speaks both dialects.** Ctrl-K accepts a one-letter prefix
  plus a space to scope the haystack — `a tolkien` searches authors,
  `s dune` series, `c` categories, `w` wings, `p` pages — with the counter
  reporting the scoped shelf; the search fallback still sees the full query.
  The `/` opener now ignores the keystroke while Ctrl/Alt/Meta is held, so
  browser shortcuts own their combos.
- **palette.js carries no second palette.** The eight hardcoded Dragon
  fallbacks (`var(--kngw-black2,#1d1c19)` and friends) are gone per
  Brandon's 2026-09-02 verdict: the palette inherits the sheet's `:root`
  tokens, the §4.2 guard question dissolves, and a missing token now fails
  visibly instead of silently diverging.
- **keynav stands down under modals.** j/k (and g/G/Enter) no longer move
  the grid while the book-detail modal, a config dialog, or any native
  `dialog[open]` is up: the handler checks Bootstrap's `modal-open` body
  class and visible `.modal.in/.modal.show` before touching focus.
- **LibraryCache transitions are serialized.** A `threading.Lock` wraps
  `get()`/`invalidate()`: two threads racing a stale mtime could both build
  (double work, and a disposed-old-value race for carrel_search); a rebuild
  is single-file now, build-before-evict semantics unchanged. A test fires
  four concurrent gets at one cache and asserts one build.
- **Currently Reading shelf on the front page.** New `cps/reading_shelf.py`
  (headless like stats.py, LibraryCache-cached): the books Calibre's own
  `reading_status` enumeration marks Reading, newest-grid page only, absent
  entirely when the column is unconfigured or empty — no fork-side state.
  The sheet gains the `.shelf` block (gray3 heading, per the contrast
  verdict below); registered in `main.py` and the test harness; the CI
  `CARREL_PY` lint list carries the new module.
- **Version 0.6.29.** Suite 82 → 92 discovered (46 base), green from the
  deployment venv.


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
