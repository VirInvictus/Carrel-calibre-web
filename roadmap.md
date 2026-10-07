# Roadmap (Carrel-calibre-web)

Created 2026-09-29 during the ecosystem parity scoping: this fork's live queue
previously lived in the companion repo's roadmap fork blocks (Carrel roadmap.md,
Waves 17-18) plus the fork's patchnotes and project.done; it now lives here. The
contract still lives in `~/.gitrepos/Carrel/` (spec.md authoritative: §6.3 the
cquarry data layer, §8.5 reader state, §11 single-user, §12.3 the stats boundary,
§13 search parity); this file records open work only. Fork point 0.6.26; branch
`smallscope`; fork version 0.6.43 (`cps/constants.py`); suite 101 tests.

**Parity lane (2026-09-29):** the web reading room, against Calibre's own Content
Server (`src/calibre/srv` in the reference clone). The read paths are
cquarry-backed or sealed; everything the upstream server offers beyond this fork's
surface (writes, conversion-on-download, reading-position writes, user management,
kobo sync) is declined by contract, not missing. The declines section below is
this repo's D-lane record for the parity ledger (cquarry roadmap.md, "The parity
program").

## Open work

- [x] **Retire the preserve_order re-sort shim with `list_books(sort="ids")`**
      (`cps/quarry_grid.py:604` signature, `:628-630` re-sort; live callers
      `web.py:532` render_hot_books and `web.py:568` render_downloaded_books).
      cquarry 1.21.0 built the mode for exactly this (its API.md names it as the
      shim's retirement); fork CI already pins cquarry v1.21.0 (`ci.yml`), so this
      is adoption only, then the shim and its parameter die. Size S.
      **Shipped 0.6.44**: the parameter and re-sort block are gone; both callers
      pass `sort=("ids",)`; a grid test pins the mode's contract (caller order,
      absent ids skipped, duplicated id keeps its first slot).
- [x] **Swap the two remaining fork-owned raw reads of metadata.db to
      `load_custom_column()`**: `reading_shelf.py:28-62` (the custom_columns lookup
      plus the two-branch normalized/direct query; `load_custom_column("reading_status")`
      plus `get_all_books()` rows retire the branch logic with it) and
      `stats.py:119-144` `_custom_column_breakdown` (same shape). stats.py's other
      raw SQL is core-table surface under spec 12.3 and stays. Size S.
      **Shipped 0.6.44**: reading_shelf's normalized/direct branch pair is gone
      (load_custom_column carries the shape; author is `min(author_sorts)`, order
      is `title_sort`, both what the SQL expressed), and the breakdown counts
      through a Counter that expands multi-valued `list[str]` columns per value,
      matching the old link-table DISTINCT-book counts. reading_shelf no longer
      imports sqlalchemy at all.
- [x] **serve_book and cover resolution still stream through the ORM**
      (`web.py:1564-1567` `get_book`/`get_book_format`; `web.py:1526-1538`
      `get_cover` -> `get_book_cover`): the last large ORM data paths (Carrel
      roadmap.md:843-846). Functional today; the swap is the sealing lane's tail.
      Size M. **Shipped 0.6.44**: serve_book reads `get_book`/`get_formats` and
      serves `get_formats`' canonical path (extension case now follows the
      catalogue, so an upper-case /show/ URL works); get_book_cover and the
      series-cover member pick (lowest id with a cover, was the ORM's unordered
      first) read cquarry behind SimpleNamespace adapters; `get_download_link`
      (the /download/ pair, same lane) came with it. The swap also carries
      upstream 84777319's access check adapted: this fork's browse layer is the
      unfiltered single-user grid, so book existence is the whole visibility
      rule. `/basic_book` stays ORM by the standing ruling. Finding along the
      way, now pinned in the harness comment: the test app auto-detects
      /opt/calibre binaries and the module default flips embed-metadata on, so
      /download used to invoke the real calibredb export against the fixture
      (whose triggerless schema calibre rebuilds destructively); the harness now
      pins `config_embed_metadata = False`, mirroring the live instance, and
      downloads in tests serve held files only.
- [ ] **`/basic_book` detail is still ORM** (`basic.py:81-84`
      `get_book_read_archived`): low priority by the standing ruling; moves only
      when it is in the way of something. Size XS.
- [x] **Upstream security cherry-picks (next fork lane; parked, not declined)**:
      8-9 substantive upstream fixes on live fork surfaces (SQLI via dbpath; the
      /show/ serve_book bypass; XXE in epub parsing; the debug_info credential
      leak; the non-admin stacktrace leak; CSP entropy; comment-column escaping;
      the download-path staged-tmp/cover-sibling pair). Recorded in both
      project.done files; re-check at the next upstream tag. Size M.
      **Shipped 0.6.44**, each verified against the live fork surface first:
      SQLI via dbpath (b5da0df4: the calibre attach was already safe through
      quote()'s URI encoding; the two unprotected app_settings literals get the
      apostrophe escape), /show/ bypass (84777319: folded into the serve_book
      swap above), XXE (224915bb: safe parsers in epub.py/epub_helper.py/fb2.py/
      goodreads_support.py; all config-gated or trimmed surfaces today, hardened
      for the day they are not), debug_info leak (d85bef6c: to_dict drops
      token/secret keys), non-admin stacktrace (fd744af7: the 500 page's stack
      is admin-only; the owner is the admin so the room is unchanged), CSP
      entropy (c23d35db: RemoteAuthToken 32 -> 128 bits; only the sealed
      kobo/remote-login paths construct one), comment-column escaping
      (42dc36cc: the clean_string filter this fork already carried in
      clean_html.py is now registered and prepended to |safe in detail.html,
      feed.xml and listenmp3.html), staged-tmp cleanup (674b47bd) and
      cover-sibling (570371cc --dont-save-cover): both on the embed-metadata
      download branches, config-off in the live instance (verified in the
      deployment's app.db), guarded for the day that changes. The code-review
      pass surfaced two siblings on the same surfaces and they landed with the
      wave: 7c715f34 (the MAIN book description sanitizes in detail.html,
      listenmp3.html and basic_detail.html, plus img joins the allowed tags)
      and 8cff413c (the attribute allowlist, so sanitized descriptions keep
      their hrefs and img srcs). And the review's kepubify finding closed the
      structural gap the wave exposed: the download embed-metadata staging
      branches (kepubify rewrite, calibre export) are stubbed declined now,
      the 0.6.40 send/convert stub family's missing member, so downloads
      serve held files only and no external binary ever runs against the
      library from that path.
- [x] **Helper adoptions when cquarry Phase 16 promotes them** (the Cross-Repo
      Implementation Rule's fork half): the ordered-VL-names helper (retires
      `cps/wings.py:33-47`), the unpiped-author display helper (retires the
      `replace("|", ",")` sites), the tag-membership id-set rollup (retires
      `cps/categories.py:29-52`), and the **Open Library ISBN switch**: `_ID_URLS`
      at `quarry_grid.py:581` moves WorldCat -> `openlibrary.org/isbn/` per
      Brandon's 2026-09-29 canonical call. Size XS each. **Shipped 0.6.43**
      against cquarry 1.25.0 (the CI pin moved v1.21.0 -> v1.25.0 with the first
      adoption). Actuals vs the row: the pipe sites numbered twenty, not nine
      (7 code, 1 filter-mirroring test, and 13 lines across 10 templates now
      using the registered `unpipe_author` Jinja filter; cps/editbooks.py keeps
      its copies -- registered-but-disabled, left venerated), and the ISBN
      switch carried the canonical table's whole shape with it: storygraph/
      mobi-asin/fictiondb/hardcover/url/uri gain buttons, kobo and douban keep
      their values as muted text without a button (babelio never matched; the
      library spells it babelio_id).
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
