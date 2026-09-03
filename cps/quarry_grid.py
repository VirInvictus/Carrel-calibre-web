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
    @property
    def format(self):
        return self._row


class _Books(_Proxy):
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
        return [_Data(fmt) for fmt in self._row["formats"] or []]


class GridEntry:
    """`entry.Books` + the `entry[2]` read-status the grid badge checks."""

    __slots__ = ("Books", "_read_status")

    def __init__(self, row, read_status=False):
        self.Books = _Books(row)
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


def grid(page, ids, sort=("sort",), descending=False, per_page=None):
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

    status = _read_status_map()
    entries = [GridEntry(row, status.get(row["id"], False)) for row in rows]
    return entries, GridPagination(max(1, page), per_page, total)


@quarry_grid.app_template_global("carrel_grid_entries")
def carrel_grid_entries():
    """Present for parity with the other Carrel template globals."""
    return None
