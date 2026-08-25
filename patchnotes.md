# Patchnotes (Carrel-calibre-web)

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
