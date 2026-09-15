# Patchnotes (Carrel-calibre-web)
## Cross-repo blitz touches (2026-09-15, logged per grant #117; no release)

Two touches from the Carrel contract repo's final-blitz lane (the fork's
own lane closed 2026-09-14 with 0.6.42); both committed on `smallscope`,
neither version-bumped, and recorded on the Carrel side of the contract:

- e7949b95: the upstream "Book N of SERIES" detail line is removed; the
  Carrel series ledger is the one statement of series placement. The same
  fact used to render twice for in-series books.
- ac000655: the canonical theme is vendored fresh (`just sync-theme`),
  carrying the dropdown theming (the last stock-white surface), the
  glyphicon tick font fix, the page-count/reader-state ledger rows, the
  ramp-comment truth, and the dead footer selector's removal. Fork suite
  86 green after both.

## The OPDS truth release: the mirrors sealed, the feeds swapped, the reader synced (2026-09-14, 0.6.42)

THE FINAL AUDIT's lane, executed top-down: both contract-truth HIGHs,
every MEDIUM, the one approved feature, and the LOW batches. The audit's
own block (bottom of this file) is ticked in place.

- **"Removed" is finally true at the OPDS boundary.** The Phase 8 seal
  never matched /opds/*, so the feeds kept serving Hot Books, Discover
  and Top Rated after the web UI lost them; the three mirrors now 404
  under the same prefix rule as their web siblings. Decision 2026-09-14
  (Brandon): seal the mirrors and swap the rest, keep the feeds.
- **The seven remaining ORM OPDS feeds read cquarry now.** The author,
  series and category letter drilldowns, the publisher, rating and
  format indexes, and the language feeds resolve names, sorts, counts
  and letter filters from the cached rows; the ORM group-bys are gone
  from every live feed but the app-DB shelf surfaces and the
  Calibre-Companion JSON (deliberate: it must serve that app's exact
  legacy shape). The language index shows names instead of raw codes and
  carries the language id its subsection link always needed: the feed
  has 500ed since Phase 7 built its Lang objects without one. Feed
  pagination clamps a zero books-per-page (the eleven ZeroDivide spots)
  through _per_page()/_page() and a guard in Pagination.pages.
- **read_book's audio branch renders from the cquarry surface.**
  get_filtered_book without allow_show_archived answered None for
  archived books and the template's cc and books_shelfs were never
  passed at all, so the Listen page has been a 500 for every audio
  book. The branch now renders the same precomputed namespace as
  show_book (pubdate falls back to the 0101 sentinel the templates
  guard on), passes cc=[] and books_shelfs=[] explicitly, and reads
  archive state from the app DB; the detail page's Archived checkbox
  shows the truth instead of a hardcoded False.
- **The Downloads prune no longer eats other pages.**
  render_downloaded_books built its prune set from the rendered page
  while walking every download id, so opening page 1 of a paged history
  deleted every later page's record; the prune now asks the library
  which downloads still exist.
- **Every category branch carries a stable data-cat key.** Implied
  branches all rendered the literal "None" and collapsed cattree's
  localStorage into one key; the sidebar list carries the full dot path.
- **The palette's Books List row is gone** (it pointed at the sealed
  /table and 404ed), and the destination test pins every page row to
  200 plus a body marker naming the thing it links.
- **Entity URLs without an id 404 instead of silently rendering entity
  1**, the trap the fixture's second series exists to catch. The
  defaults loop uses a 0 sentinel: werkzeug treats a None default as no
  default, which would break the grid footer's pagination build.
- **The dead Phase 7 scaffold is swept** (full sweep, Brandon's call):
  detail_entry (crash-if-called twice over), _detail_books_proxy, the
  grid-side _IDENTIFIER_* half with _Books.identifiers/ordered_authors,
  the _Books reader and audio proxies, the carrel_grid_entries stub,
  and the no-op ordered_authors self-assignment. build_detail now
  derives reader_list/audio_entries from the surviving frozensets
  instead of shipping empty placeholders for show_book to overwrite.
- **Reading-position sync and a Continue Reading row**, the blitz's one
  approved feature: with no app-DB bookmark, the epub reader opens at
  the device-recorded position (last_read_positions via cquarry; the
  browser's own saved position wins where it has one), and the front
  page lists device-touched books most recent first with a percent.
  Zero library writes. Slotted set recorded: only this pair; page-flip
  keys, next-in-series, the highlights viewer (its spec 8.5 amendment
  is still pending in the Carrel repo), navigable statistics, column
  h/l and the /basic pair are declined this blitz. The Kindle-path
  answer (2026-09-14): the Oasis reads through Calibre's own web server
  and KOReader's Calibre integration, so /basic is not a device surface.
- **The papercuts.** A vanished library answers 503 from the wings,
  saved-search and category routes (the Phase 13 convention) instead of
  a lying 404; category URLs match case-insensitively; /basic's garbage
  ?page degrades to the first page; the context processors probe the
  library once per request instead of opening a sqlite connection each;
  the two rendered em-dashes (the palette placeholder, the statistics
  tooltip) are recast.
- **Comments say what the code does.** Five mtime-only cache headers
  mention the UUID; series_info's "max" story is true; the cc block
  records its waiver; the four "kanagawa spec" misnomers point at
  Carrel's spec; the URL-shape trap comment sits at the defaults loop;
  build_detail's docstring marks read_status/is_archived as route-owned
  placeholders.
- **Docs and environment.** README gains the OPDS section and scopes
  its Removed list to the web UI; CLAUDE.md's module table catches up
  on library_cache and page_count and records the hardening; the three
  NEW-AUDIT.md pointers carry dated errata naming the real ledger. CI
  moves to actions v7 and pins cquarry at v1.21.0, the tag the
  deployment venv loads (suite run from that venv). The branch-guard
  hooks are installed host-side (uncommitted, .git/hooks), gh's default
  repo points at the fork, the description no longer claims
  localhost-only, four topics joined, wiki and Projects toggles off,
  and Releases exist for v0.6.40 and v0.6.41 (the backfill stays
  declined). The upstream FUNDING.yml and issue templates are deleted.
- **Version 0.6.42.** Suite 86 green.

## Categories beneath Wings, the palette off the ORM, the honest decorator count (2026-09-13, 0.6.41)

The fork half of Carrel's v0.9.9 lane (decision 2026-09-12: a compact
Categories section beneath Wings).

- **The sidebar re-balances: Categories now renders beneath Wings.**
  Wings lead as the curated structure; the compact Categories index sits
  between them and Saved Searches. The compact register is the theme's
  (tighter rows, a half-step down in type), shipped through the canonical
  sheet and `just sync-theme`; a regression test pins the order against
  the nav-head markers.
- **palette.py's entity reads go through cquarry get_entities().** The
  authors/series/tags queries were the fork's Carrel modules' last ORM
  reads; the Ctrl-K index now shares one source with the about-page
  counts and the OPDS feeds. Same payload set, name-ordered instead of
  id-ordered; every palette href still lands on its own target (the
  existing tests hold, and a new lockstep test pins the index to
  get_entities' output).
- **single_user.py's decorator count is corrected.** The header comment
  claimed upstream carries 154 @login_required decorators across 10
  modules; measured, it is 39 across 5 upstream modules (42 across 10 at
  smallscope HEAD counting the fork's own). The roadmap's claim that
  this fix shipped in 230c42bc was false; it lands here.
- Screenshots regenerated for the new sidebar order (front page, detail,
  statistics, category tree). Suite: 73 green.

## Phase 13 sealing release: eight routes sealed, send/convert dead, the invariants pinned (2026-09-11, 0.6.40)

The fork half of the contract repo's Phase 13 hardening backlog (the
sweep that prompted it is recorded there). The headline: eight live
routes the credential seal never met are sealed; the send/convert chain
can no longer write into the library folder regardless of configuration;
the read-only attach and the harness's blueprint parity are pinned by
committed tests.

- **Eight admin-machinery routes sealed.** /get_updater_status (whose
  start=True resumes the updater thread that would replace the checkout
  with an upstream release, destroying the smallscope patches),
  /get_update_status, the user AJAX trio (/ajax/listusers,
  /ajax/editlistusers/<param>, /ajax/deleteuser: deleting the owner
  bricks the room), /ajax/pathchooser (an arbitrary directory listing),
  /shutdown, /reconnect. One frozenset extension and one prefix tuple in
  single_user.py's existing rebase-friendly pattern; the probed kill
  chain was two unauthenticated requests with self-mintable CSRF.
- **The send/convert chain is dead structurally.** send_mail and
  convert_book_format refuse before touching the ORM, so no
  configuration state can queue ebook-convert, which writes a converted
  file INTO the library folder (the read-only commit only failed closed
  by operation order). TaskBackupMetadata refuses outright: it wrote
  metadata.opf into book folders on the same order-only guarantee.
- **One broken wing or saved search no longer poisons its section.**
  Resolution is per-name now: a vl: target renamed in Calibre, or a
  saved-search name containing a quote, is skipped and logged while its
  siblings survive. Before, the failed rebuild never updated the cache
  mtime, so every page render re-paid it and the whole section vanished
  until the entry was fixed in Calibre desktop.
- **OPDS hardening.** A new _int_param() replaces all 22 bare int()
  offset reads (garbage degrades to the first page instead of escaping
  as a 500); an unparseable search query renders an empty feed instead
  of 500ing; the search feed pages at the configured books-per-page with
  feed.xml's existing rel="next", instead of rendering every match in
  one unbounded response with full comments.
- **Honest failure classes.** resolve() converted every exception,
  including a vanished metadata.db, into "could not parse that search".
  Parse errors stay SearchError; an unreadable library now raises
  LibraryUnavailable, answered 503 by /search and /basic (the
  /statistics convention) and by the empty feed in OPDS. Wing and
  saved-search URLs are case-insensitive like every surface beneath
  them.
- **The invariants are committed tests now.** PRAGMA database_list pins
  the mode=ro attach to the single pooled connection beside the existing
  refused-UPDATE probe; a parity test parses main.py's blueprint
  registrations with ast and compares against the harness in both
  directions (the drift that once silently voided the Phase 8 route
  cuts), with kobo/oauth/gdrive pinned off; the new seals have a
  method-exact regression test.
- **Papercuts.** The vacuous assertGreaterEqual in the custom-column
  test is assertGreater; TestQuarryExtensions no longer re-runs the 48
  parent tests, so collected equals executed; clean_html.py is reverted
  to upstream byte-for-byte (the reformat had stripped its GPL-3.0
  header) and about.py keeps its two functional lines without the
  quote-style reflow; CI pins the cquarry install to v1.17.0 instead of
  @main.
- **Requires cquarry >= 1.11.1.**
- **Version 0.6.40.** Suite 71 green (was 108 executions for 60 unique
  tests).

## Phase 7 close: read_book through cquarry; rebrand light-touch (2026-09-04, 0.6.39)

- **read_book route swapped.** The ORM `get_filtered_book` call is
  replaced by `quarry_grid.build_detail(book_id)`, same as show_book.
  The epub/pdf/txt/djvu reader branches work from the precomputed
  surface. *(Corrected 2026-09-05: the audio branch still resolves the
  book through `get_filtered_book` and passes the ORM object to
  `listenmp3.html`; only the top-of-route call moved.)*
- **Rebrand light-touch.** Upstream copyright headers stripped from
  Carrel-owned files that were rewritten from scratch (clean_html.py).
  Stock calibre-web files (web.py, db.py, helper.py, config_sql.py)
  keep their upstream headers: they are still substantially upstream
  code. README identity is already Carrel-first.
  *(Corrected 2026-09-11: clean_html.py was NOT rewritten from
  scratch. It exists at the 0.6.26 base and this branch's diff was a
  pure whole-file reformat with zero functional change that also
  stripped upstream's GPL-3.0 header from third-party code. The file
  is reverted to upstream byte-for-byte; whether the CI lint list or
  the ownership claim should bend to that is Brandon's call, drafted
  in Carrel's roadmap.)*
- **Version 0.6.39.** Suite 108 green.

## Phase 7: show_book through cquarry's build_detail (2026-09-04, 0.6.38)

- **show_book route swapped.** The ORM `get_book_read_archived` call is
  replaced by `quarry_grid.build_detail(book_id)`, which precomputes the
  detail-page surface from cquarry: hydrated row with authors, tags,
  languages, formats with sizes, identifiers, comments, publishers,
  series, rating, pubdate, has_cover, and the `title_sort` field. The
  SimpleNamespace also carries `author_sort` for the ordered_authors
  chain.
- **Version 0.6.38.** Suite 108 green.

## Phase 7: DetailProxy scaffold (2026-09-04, 0.6.37)

- **`quarry_grid._Books` grew the detail-page surface**: ordered_authors
  (entity id map), identifiers with `format_type()` and vendor URLs
  (`_IdentifierProxy`), `reader_list` / `audio_entries` (derived from
  formats), per-format `uncompressed_size` via `formats_map`, and
  `__getitem__` for the custom_column_N accessor (returns []: the cc
  adapter is a documented deferral). `_READER_FORMATS` / `_AUDIO_FORMATS`
  constants defined.
- **`detail_entry()`** stubs the cquarry-backed detail builder: fetches
  the dossier, builds the enriched proxy + cc metadata list. The
  show_book route still runs on the ORM (the swap is the next session's
  work: the scaffold is tested and the proxies are proven by the suite).
- **Version 0.6.37.** Suite 108 green.

## Phase 7 wrap: /ajax/listbooks sealed, advsearch code deleted, slop pass (2026-09-03, 0.6.36)

- **The books-table zombie is sealed.** /table, /ajax/listbooks, and
  /ajax/table_settings join the sealed prefixes: no sidebar link exists,
  every write button on that page already 404s (editbook blueprint
  trimmed), and the read side is the last big AlchemyEncoder consumer.
  Sealing is reversible; deletion can ride the rebrand.
- **The advsearch code behind its seal is deleted.** /advsearch was
  already 404-sealed (spec 13.2a: one grammar or none); the ~500 lines
  of dead ORM behind it (routes, adv_search_* helpers,
  render_adv_search_results, render_prepare_search_form, the
  flask_session handshake, search_form.html) are gone. The seal now has
  nothing behind it to rot.
- **Slop pass (dragon-agents slop-reader):** the em-dash habit it flagged
  across NEW-AUDIT.md and these patchnotes is purged (about 40 instances
  recast to colons/semicolons), plus a duplicated instruction passage, a
  duplicated resolution line, a future-dated line, and one "robust".
  *(Erratum 2026-09-14: NEW-AUDIT.md exists in neither repo; the audit
  ledger meant here is audit-final/Carrel-calibre-web/FINAL-REPORT.md.)*
- **Version 0.6.36.** Suite 108 green.

## Phase 7: OPDS through cquarry (2026-09-03, 0.6.35)

- **The OPDS book-list feeds run on cquarry now**: newest, letter books
  and the books A–Z index, discover (random via sample), best-rated,
  series, the four dataset feeds (author/publisher/category/ratings),
  formats, language index, and the search feed, which now speaks the
  same grammar as the search bar (via `carrel_search.resolve`) instead
  of the old ORM wildcard match. Letter indexes are computed in Python
  from cquarry rows instead of SQL group-bys.
- **`quarry_grid` proxies grew the OPDS surface**: uuid, atom_timestamp,
  pubdate as a datetime, publishers/languages/tags, comments (a batch
  comment fetch per feed render), per-format `uncompressed_size` (lazy
  via `get_formats`), `has_cover`, and `GridPagination` gained
  `next_offset`/`previous_offset` for the feed's rel links.
- **Deliberately deferred inside OPDS**: the custom-column content block
  (needs a cc adapter with series `.extra`: the feed renders without
  it; ratings/tags/series/comments remain), the hot and shelf feeds
  (app-DB-coupled), and the Calibre-Companion JSON endpoint (wants
  `get_book_by_uuid`, a 1.12 candidate). The shelf orphan-cleanup and
  download-count app-DB writes are unchanged.
- **Version 0.6.35.** Suite 102 → 108 discovered (54 base): OPDS feeds
  parse as XML with full entries, the search feed resolves the cquarry
  grammar, and the letter indexes render.

## Phase 7: the last grids join the swap; dead code out (2026-09-03, 0.6.34)

- **Archived, read/unread, hot, and downloaded grids page through
  cquarry.** Archived and read/unread resolve id sets (app-DB archived
  ids; the read map in `quarry_grid.read_ids`) and page via
  `quarry_grid.grid`, which gained a `preserve_order` mode for callers
  carrying their own ordering: hot books keep their download-count
  order from the app DB, downloaded books their user-download order.
  Dead downloads are pruned exactly as the old per-book loops did. The
  OPDS read/unread feeds stay on the ORM for now (feed.xml's rich entry
  surface: they swap with opds.py itself), as does the ub.ReadBook
  fallback for column-less instances.
- **/basic_book detail and the about-page counts.** `/basic` search was
  already cquarry-backed; the about page's four
  counts now come from `count_books()` + `get_entities()` instead of ORM
  session queries. *(Corrected 2026-09-05: `/basic_book` was NOT already
  cquarry-backed and still is not; it remains the last ORM detail
  surface.)*
- **Dead code out.** The commented-out `get_comic_book` block is deleted,
  and `edit_book_read_status` loses its unreachable bool-column write
  branch: any configured read column is now simply read-only here.
- **Version 0.6.34.** Suite 102 green. Remaining Phase 7: opds.py (the
  biggest piece), show_book/read_book detail surface, /ajax/listbooks,
  adv_search: planned in NEW-AUDIT.md's Stage 6 box. *(Erratum
  2026-09-14: NEW-AUDIT.md exists in neither repo; the Stage 6 map lives
  in audit-final/Carrel-calibre-web/FINAL-REPORT.md.)*

## Phase 7: the browse grids join the swap (2026-09-03, 0.6.33)

- **Every entity browse grid now pages through cquarry.** Author,
  publisher, series, category, language, ratings, formats, rated, and the
  newest default grid resolve their book-id sets rows-side
  (`quarry_grid.ids_for_entity` / `ids_missing` / `ids_with` over the
  cached rows: entity id → name/value → row match; no per-entity
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
  `SEARCH_SORTS` map carries the sort header onto `list_books` keys :
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
  the cache arrives pre-sorted: found by this fork's descending search
  sort, fixed upstream in the same wave.
- Suite 100 → 102 discovered (51 base): the sort-header test now exercises
  the cquarry path (and caught the upstream bug), plus grid/pagination
  unit tests and /basic grammar + degradation coverage.

## Phase 7: the hybrid unwinds (2026-09-03, 0.6.31)

- **Wings, saved searches, and categories page through cquarry now.** The
  three surfaces resolved their book-id sets through cquarry's search
  engine but still paged them through the stock ORM `fill_indexpage` :
  the hybrid the boundary map called out. New `cps/quarry_grid.py`
  finishes the swap: cquarry 1.10's `list_books()` pages the rows, and a
  clean-room adapter builds exactly the attribute surface `index.html`
  renders (`entry.Books.title/series[0].id/ratings[0].rating/authors/
  data`, the `entry[2]` read badge from the read column, and a
  Flask-shaped pagination shim with ellipsis arithmetic). The ORM and
  its query builders are off these pages entirely.
- **The categories rollup too.** `_rollup()`'s tag→book pairs come from
  cquarry's cached rows (every book row carries its tags) instead of an
  ORM session query: same implied-prefix rule.
- **A falsy-empty trap the tests caught**: `grid()` treated an empty
  id-set as "the whole library" (bare `if ids`), which would have made
  the saved search matching nothing render every book: the exact bug
  the "renders not 404s" test guards. `None` means everything; an empty
  set means an empty page, and the distinction is now explicit and
  test-pinned.
- **Version 0.6.31.** Suite 96 → 100 discovered (50 base). Remaining
  Phase 7 surface (web.py, opds.py, search.py results assembly,
  basic.py) stays future work, scoped by the boundary map.

## Phase 7 begins: the data-layer swap's first increments (2026-09-03, 0.6.30)

The NEW-AUDIT Stage 6 boundary map classified every cps/db.py call site
*(erratum 2026-09-14: NEW-AUDIT.md exists in neither repo; the map is the
audit ledger at audit-final/Carrel-calibre-web/FINAL-REPORT.md)*;
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
  `analytics.addition_timeline()`: the derivation is database-shaped, so
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
  plus a space to scope the haystack: `a tolkien` searches authors,
  `s dune` series, `c` categories, `w` wings, `p` pages: with the counter
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
  entirely when the column is unconfigured or empty: no fork-side state.
  The sheet gains the `.shelf` block (gray3 heading, per the contrast
  verdict below); registered in `main.py` and the test harness; the CI
  `CARREL_PY` lint list carries the new module.
- **Version 0.6.29.** Suite 82 → 92 discovered (46 base), green from the
  deployment venv.


## cquarry 1.8 sync + editable install (2026-08-26 → 0.6.28, 2026-08-30)

- **Deployment venv reinstalled EDITABLE from `~/.gitrepos/cquarry`** (Carrel
  spec §8.2's documented contract). The stale non-editable cquarry 1.1.1 in
  site-packages predated the branch's 1.3 API calls: the running instance
  silently degraded page_count to None. Installed == repo now, and it cannot
  drift again.
- **`cps/library_cache.py`'s UUID read adopts cquarry's URI contract.** The
  "deliberately does NOT go through cquarry" note was a stale-install
  artifact, not architecture: the Phase 4 venv predated `get_library_uuid()`.
  The read stays a single one-query mode=ro connection (a full CalibreDB
  lifecycle would regress the per-cache-hit cost the module exists to keep
  cheap), but the URI now comes from cquarry's `db_uri_ro()`: whose
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
  `carrel_page_count(book_id)` follows the reader_state pattern: answers or
  says None, never 500s: and detail.html renders a "Pages" line only when the
  library actually knows.
- **Library-identity cache invalidation (`cps/library_cache.py`).** The six
  LibraryCache surfaces (wings, categories, search, series, statistics,
  palette: plus reader state and page count) now key on metadata.db's mtime
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
  interpolation: cycle detection, strict errors on unknown names, and exact
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

## Final audit 2026-09-13 (THE FINAL AUDIT — logged, not shipped; full detail in audit-final/Carrel-calibre-web/FINAL-REPORT.md)
- [x] **HIGH — CONFIRMED: the contract's cut/OPDS claims are not yet true: nine OPDS routes still read through the ORM and still serve the "removed" surfaces (/opds/hot, discover, best-rated, the letter drilldowns, publisherindex, the Calibre-Companion JSON) because _SEALED_PREFIXES never matches /opds/*; reader CONTENT still streams via serve_book's ORM resolve while spec §6.3's blanket claim covers "the read surfaces"; README's "Removed" states web-UI-only truth as absolute.** Brandon's call: extend the seal to /opds/* vs swap the nine feeds to cquarry; either way the docs change.
- [x] **HIGH — CONFIRMED: read_book's audio branch 500s on archived books (web.py:2154, get_filtered_book without allow_show_archived → UndefinedError).** Fold into the boxed audio-branch swap.
- [x] MED — render_downloaded_books prunes the whole download history against the current page (web.py:562-572: `have` from one page, the delete loop walks ALL download_ids); scope the prune like render_hot_books.
- [x] MED — every implied-prefix category branch renders data-cat="None", collapsing cattree's localStorage into one key (expand one, they all re-open); emit a stable key.
- [x] MED — the dead-scaffold sweep (one commit): detail_entry + _detail_books_proxy (crash-if-called via __slots__, zero callers), the ENTIRE grid-side _IDENTIFIER_* half incl. _Books.identifiers/ordered_authors (zero consumers — this dissolves the recorded consolidation into a removal), carrel_grid_entries + its blueprint cascade, the web.py:2112 no-op self-assignment. Optionally _READER_FORMATS/_AUDIO_FORMATS + the two proxy properties (waive if kept for OPDS growth).
- [x] MED — palette "Books List" → sealed /table: drop or repoint; tighten the destination test to assert 200 + body marker.
- [x] MED — the entity-URL hardening (queued): abort(404) when book_id is absent in the add_url_rule defaults loop (16 data values × 2 rules silently default to 1).
- [x] MED — environment truth: gh's default repo for this working directory is UPSTREAM (gh repo set-default VirInvictus/Carrel-calibre-web); CI's cquarry pin is @v1.17.0 while the deployment venv loads 1.21.0 (bump + one suite run from the deployment venv); the "smallscope only" rule has zero enforcement while the deployment runs this working tree (local uncommitted branch-guard hook).
- [x] MED — GitHub: description still claims "localhost-only" (false since the 0.0.0.0 rebind; it is the <title> and social card); zero Releases behind 9 pushed tags (cut v0.6.40/41 verbatim; backfill decision Brandon's); the Sponsor button routes to upstream's PayPal (delete .github/FUNDING.yml, prune ISSUE_TEMPLATE); four topic additions; wiki + Projects toggles off; the codex page (live, gated item RESOLVED) still carries "154 decorators" and pre-rebalance counts (VirInvictus.github.io lane).
- [x] LOW — feed_languagesindex surfaces raw lang_codes ("eng" not "English"); basic.py:48 unguarded int(?page) → ValueError 500 (reuse _int_param); config_books_per_page=0 ZeroDivides in eleven OPDS spots; entry.is_archived hardcoded False on the detail page; read_ids hardcodes 'reading_status'/'Read' ignoring config_read_column; 404-vs-503 inconsistency across categories/wings/saved_searches; category URLs case-sensitive vs case-insensitive siblings; rendered em-dashes in palette.js/statistics.html; six context processors each re-open sqlite per render (one per-request snapshot); .gitignore lacks the tool-cache rules (stray cps/templates/.ruff_cache from a mis-cwd run).
- [x] LOW — comment truth: the harness comment says "enable the caliBlur theme" while the code sets config_theme = 0; series_info claims "max" is not exposed (it is returned and exposed, just unrendered); build_detail's docstring presents hardcoded read_status/is_archived as surface, not placeholders; five module headers say mtime-only (mtime+UUID since 0.6.28); the DetailProxy banner sits over the dead scaffold; the cc-block comment says "until a cc adapter lands" (WAIVED); the no-op elif in _entity_name_map; layout.html "kanagawa spec 8" misnames the contract; reader_state docstring says epoch_time (the key is epoch); one trap comment at the add_url_rule loop itself; quarry() examples predate the OPDS consumers. Organization: quarry_grid is three modules in one file (split or section-order); generate the blueprint mirror from one source.
- [x] LOW — docs: README lacks an OPDS section entirely (the fork's largest surface); "71 tests" vs 73 (update on release); curly-apostrophe paste seam at README:53-57; palette/mobile screenshots predate 0.6.29/0.6.41 (regenerate); CLAUDE.md module table missing library_cache.py + page_count.py; mtime-only cache wording; patchnotes reference NEW-AUDIT.md (exists in neither repo — tie to the errata policy); ci.yml actions v5→v7.
- [x] Feature candidates logged (FINAL-REPORT L4, ranked): reading-position sync (consume half of §8.5; the bookmark-fallback shape) + continue-reading row (one extractor); keynav page-flip keys + `?` overlay + palette prefix-aware fallback (one small release); next-held-book-in-series detail link (804 series); highlights viewer on the detail page (needs the §8.5 count→count-plus-excerpts amendment); navigable statistics rows (template-side links, §12.3 intact); column-wise h/l; the /basic pair (gated on the Kindle-path answer). Declined: palette title indexing, anything writing reading_status (waived), OPDS additions (waived 2026-09-11).

**CONFIRMED-prior (final-audit verification):** the audio-branch 500, the OPDS seal gap, the /table row, the entity-URL trap, the ORM OPDS surfaces, detail_entry, metadata_backup bodies, the GitHub batch. WITHDRAWN/REFUTED cross-repo: the Carrel-side decorator HIGH (the numbers verify under the if_no_ano spelling: 39-across-5 at the merge-base, 42-across-10 at HEAD) and the Carrel-side checksum-proof LOW (the md5 tests exist at tests/test_smallscope.py:190-211). Audit-side correction: the sheet's "108 collected, 60 unique" is stale (73 collected and executed). Slop-reader verdict: human end to end; the smart-quote paste block and the stale test count are the only prose work.
