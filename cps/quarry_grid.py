# -*- coding: utf-8 -*-

# The cquarry-backed grid (Carrel Phase 7).
#
# Wings, saved searches, and categories all resolve a book-id set through
# cquarry's search engine and then page it. Until now the paging half ran
# through the stock ORM `fill_indexpage`, which meant every Carrel surface
# still dragged the calibre-web query machinery along for one JOIN. This
# module finishes that swap: cquarry 1.10's `list_books()` pages the rows,
# and this file adapts them to the attribute surface `index.html` renders —
# `entry.Books.title`, `entry.Books.series[0].id`, `entry[2]` for the read
# badge, and a pagination shim with the Flask-SQLAlchemy shape. Clean-room
# against cquarry's row dicts (the fork is GPL, cquarry is MIT; only calls
# flow this direction).
#
# What the templates touch is deliberately the whole adapter surface. If a
# template grows a new attribute, grow the proxy here — never reintroduce
# the ORM on these pages.

from datetime import datetime

from flask import Blueprint

from . import config, logger
from .library_cache import quarry

quarry_grid = Blueprint("quarry_grid", __name__)
log = logger.create()

# A blueprint only so Flask gives us app_template_global registration; it
# has no routes of its own.


class _Proxy:
    __slots__ = ("_row",)

    def __init__(self, row):
        self._row = row


class _Author(_Proxy):
    @property
    def id(self):
        return self._row["id"]

    @property
    def name(self):
        return self._row["name"]


class _Series(_Proxy):
    @property
    def id(self):
        return self._row["id"]

    @property
    def name(self):
        return self._row["name"]


class _Rating(_Proxy):
    @property
    def rating(self):
        return self._row["rating"]


class _Data(_Proxy):
    # _row is the format name; the owning book id enables the lazy size
    # lookup (feed.xml's length attribute; index.html never asks).
    def __init__(self, fmt, book_id):
        super().__init__(fmt)
        self._book_id = book_id

    @property
    def uncompressed_size(self):
        try:
            fmts = quarry().get_formats(self._book_id) or {}
            return (fmts.get(self._row) or {}).get("size_bytes")
        except Exception:
            return None

    @property
    def format(self):
        return self._row


class _Books(_Proxy):
    def __init__(self, row, comments_map=None):
        super().__init__(row)
        self._comments_map = comments_map or {}

    @property
    def id(self):
        return self._row["id"]

    @property
    def title(self):
        return self._row["title"]

    @property
    def series_index(self):
        return self._row["series_index"]

    @property
    def last_modified(self):
        # image.html's cache-buster filter calls .timestamp(); cquarry rows
        # carry Calibre's TEXT form, so parse once here.
        raw = self._row["last_modified"]
        try:
            return datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            return datetime(1970, 1, 1)

    @property
    def authors(self):
        ids = _name_ids("authors")
        out = []
        for name in self._row["authors"] or []:
            out.append(_Author({"id": ids.get(name), "name": name}))
        return out

    @property
    def series(self):
        name = self._row["series"]
        if not name:
            return []
        sid = _name_ids("series").get(name)
        if sid is None:
            return []
        return [_Series({"id": sid, "name": name})]

    @property
    def ratings(self):
        rating = self._row["rating"]
        return [_Rating({"rating": rating})] if rating else []

    @property
    def data(self):
        return [_Data(fmt, self._row["id"]) for fmt in self._row["formats"] or []]

    @property
    def uuid(self):
        return self._row["uuid"]

    @property
    def has_cover(self):
        return bool(self._row["has_cover"])

    @property
    def title_sort(self):
        return self._row["title_sort"]

    def _parsed(self, field):
        raw = self._row[field]
        try:
            return datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            return datetime(101, 1, 1)

    @property
    def atom_timestamp(self):
        # OPDS updated stamps (feed.xml) — same format the ORM property used.
        return self.last_modified.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    @property
    def pubdate(self):
        return self._parsed("pubdate")

    @property
    def publishers(self):
        name = self._row["publisher"]
        return [_Series({"id": None, "name": name})] if name else []

    @property
    def languages(self):
        return [
            _Series({"id": None, "name": code}) for code in self._row["languages"] or []
        ]

    @property
    def tags(self):
        return [_Series({"id": None, "name": name}) for name in self._row["tags"] or []]

    @property
    def comments(self):
        html = self._comments_map.get(self._row["id"]) if self._comments_map else None
        return [_Series({"name": html, "id": None})] if html else []

    def __getitem__(self, key):
        # custom_column_N access (feed.xml's cc block): the cquarry-backed
        # feed passes cc=[], so this stays empty until a cc adapter lands.
        return []

    def get(self, key, default=None):
        return default


class GridEntry:
    """`entry.Books` + the `entry[2]` read-status the grid badge checks."""

    __slots__ = ("Books", "_read_status")

    def __init__(self, row, read_status=False, comments_map=None):
        self.Books = _Books(row, comments_map=comments_map)
        self._read_status = read_status

    def __getitem__(self, idx):
        if idx == 2:
            return self._read_status
        raise IndexError(idx)


class GridPagination:
    """The slice of the Flask-SQLAlchemy Pagination shape index.html uses."""

    def __init__(self, page, per_page, total):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, -(-total // per_page)) if per_page else 1

    @property
    def next_offset(self):
        return self.page * self.per_page if self.has_next else None

    @property
    def previous_offset(self):
        return (self.page - 2) * self.per_page if self.has_prev else None

    @property
    def total_count(self):
        # the name the read/unread titles use for the total
        return self.total

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
        # Mirrors flask_sqlalchemy's default pagination arithmetic: the
        # edge ranges, a window around the current page, and None marking
        # each ellipsis gap (one None per contiguous gap, like Flask's).
        last = self.pages
        shown = set()
        for num in range(1, last + 1):
            if (
                num <= left_edge
                or num > last - right_edge
                or self.page - left_current <= num <= self.page + right_current
            ):
                shown.add(num)
        gap_open = False
        for num in range(1, last + 1):
            if num in shown:
                yield num
                gap_open = False
            elif not gap_open:
                yield None
                gap_open = True


_entity_caches = {}


def _name_ids(kind):
    """{name: entity id} for authors/series, cached per library generation.

    The cache clears with the same signal the grids rebuild on: the quarry
    handle's LibraryCache invalidates on mtime/UUID, and the entity maps are
    derived from it, so they are cached against the quarry object itself.
    """
    quarry_db = quarry()
    cache = _entity_caches.setdefault(kind, {"db": None, "map": None})
    if cache["db"] is not quarry_db:
        cache["db"] = quarry_db
        cache["map"] = {e["name"]: e["id"] for e in quarry_db.get_entities(kind)}
    return cache["map"]


# Entity kinds the browse grids resolve, mapped to the row field that
# carries the match value: an entity's books are the cached rows whose
# field contains the entity's name/value. Rows-side resolution needs no
# new cquarry API and no per-entity queries.
_ENTITY_ROW_FIELDS = {
    "authors": "authors",
    "series": "series",
    "publishers": "publisher",
    "tags": "tags",
    "languages": "languages",
    "formats": "formats",
    "ratings": "rating",
}


def _entity_name_map(kind):
    """{entity id: match value} for one kind, from get_entities()."""
    quarry_db = quarry()
    out = {}
    for e in quarry_db.get_entities(kind):
        value = e["name"]
        if kind == "ratings":
            # get_entities surfaces the rating value as its name (text).
            value = int(value)
        elif kind in ("authors", "series"):
            value = e["name"]
        out[e["id"]] = value
    return out


def ids_for_entity(kind, entity_id):
    """Book ids linked to one entity, ascending. Unknown ids give []."""
    try:
        entity_id = int(entity_id)
    except (TypeError, ValueError):
        return []
    field = _ENTITY_ROW_FIELDS[kind]
    wanted = _entity_name_map(kind).get(entity_id)
    if wanted is None:
        return []
    out = []
    for row in quarry().get_all_books():
        have = row.get(field)
        if isinstance(have, list):
            if wanted in have:
                out.append(row["id"])
        elif have == wanted:
            out.append(row["id"])
    return sorted(out)


def entity_name(kind, entity_id):
    """The entity's raw display name/value, or None when the id is unknown.
    Ratings come back as the integer value; authors keep Calibre's raw
    pipe-escaped form (callers decide the display transform)."""
    try:
        entity_id = int(entity_id)
    except (TypeError, ValueError):
        return None
    return _entity_name_map(kind).get(entity_id)


def ids_with(field, value):
    """Book ids whose row field contains `value` (list fields: membership;
    scalar fields: equality), ascending."""
    out = []
    for row in quarry().get_all_books():
        have = row.get(field)
        if isinstance(have, list):
            if value in have:
                out.append(row["id"])
        elif have == value:
            out.append(row["id"])
    return sorted(out)


def read_ids(are_read):
    """Book ids for the read/unread grids: 'Read' in the library's
    reading_status enumeration (or its complement)."""
    status = _read_status_map()
    read = {i for i, v in status.items() if v == "Read"}
    if are_read:
        return sorted(read)
    return sorted(i for i in all_ids() if i not in read)


def ids_missing(kind):
    """Book ids with NO value for one kind (the 'None' browse variants:
    untagged, no publisher, no language, no formats, unrated)."""
    field = _ENTITY_ROW_FIELDS[kind]
    return sorted(row["id"] for row in quarry().get_all_books() if not row.get(field))


def all_ids():
    """Every book id, ascending."""
    return sorted(row["id"] for row in quarry().get_all_books())


def _read_status_map():
    try:
        return quarry().load_custom_column("reading_status") or {}
    except Exception as ex:
        log.info("read column unavailable: %s", ex)
        return {}


# The search page's sort-header tokens mapped onto list_books keys.
# authaz/authza are the ORM's exact shape: author_sort primary, series
# name then series index tie-breaking, one direction for all.
SEARCH_SORTS = {
    "stored": (("sort",), False),
    "abc": (("sort",), False),
    "zyx": (("sort",), True),
    "new": (("timestamp",), True),
    "old": (("timestamp",), False),
    "authaz": (("author_sort", "series", "series_index"), False),
    "authza": (("author_sort", "series", "series_index"), True),
    "pubnew": (("pubdate",), True),
    "pubold": (("pubdate",), False),
    "seriesasc": (("series_index",), False),
    "seriesdesc": (("series_index",), True),
}


def search_sort(sort_param):
    """(keys, descending) for a search-page sort token; unknown falls to
    the title-sort default."""
    return SEARCH_SORTS.get(sort_param, (("sort",), False))


def grid(
    page,
    ids,
    sort=("sort",),
    descending=False,
    per_page=None,
    preserve_order=False,
    include_comments=False,
):
    """(entries, pagination) for one page of the given book-id set.

    `ids=None` means the whole library; an EMPTY set means an empty page.
    Sorted by Calibre's title-sort unless the caller passes a sort shape
    (see SEARCH_SORTS). Page size is the instance's configured
    books-per-page.
    """
    per_page = per_page or config.config_books_per_page or 60
    quarry_db = quarry()
    # None means the whole library; an EMPTY set means an empty page. A
    # bare `if ids` would render every book for a saved search that
    # matches nothing (the falsy-empty trap the saved-search contract
    # explicitly guards against).
    wanted = None if ids is None else list(ids)
    all_rows = quarry_db.list_books(ids=wanted, sort=sort, descending=descending)
    total = len(all_rows)
    offset = (max(1, page) - 1) * per_page
    rows = all_rows[offset : offset + per_page]
    # Callers that carry their own ordering (download counts, shelf order)
    # get their id sequence back verbatim; list_books otherwise sorts by
    # its keys.
    if preserve_order and wanted:
        row_order = {bid: n for n, bid in enumerate(wanted)}
        rows = sorted(rows, key=lambda r: row_order.get(r["id"], len(row_order)))

    status = _read_status_map()
    comments = None
    if include_comments:
        try:
            comments = quarry_db.get_comments()
        except Exception:
            comments = None
    entries = [
        GridEntry(row, status.get(row["id"], False), comments_map=comments)
        for row in rows
    ]
    return entries, GridPagination(max(1, page), per_page, total)


@quarry_grid.app_template_global("carrel_grid_entries")
def carrel_grid_entries():
    """Present for parity with the other Carrel template globals."""
    return None
