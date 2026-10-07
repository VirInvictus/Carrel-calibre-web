# -*- coding: utf-8 -*-

# The Currently Reading shelf (Carrel Phase 12).
#
# The front page answered "what is new"; for a reader mid-book the more
# useful question is "what am I reading". The answer comes from the library's
# own reading_status enumeration — no fork-side state — so the shelf shows
# exactly what Calibre says is in progress, and is absent entirely when the
# column is unconfigured, not normalized, or simply has nothing in flight.
# Headless like stats.py: plain data in, template decides the rendering.

from flask import Blueprint

from . import logger
from .library_cache import LibraryCache

reading_shelf = Blueprint("reading_shelf", __name__)
log = logger.create()

SHELF_VALUE = "Reading"
LIMIT = 12


def _build():
    """[{id, title, author, href}] for the books Calibre marks Reading."""
    from .library_cache import quarry

    try:
        quarry_db = quarry()
        statuses = quarry_db.load_custom_column("reading_status")
    except Exception as ex:
        # An unconfigured column, an unnormalized one, an unreadable
        # library: all degrade to the absent shelf.
        log.info("reading_status column unreadable: %s", ex)
        return []
    reading = [bid for bid, value in statuses.items() if value == SHELF_VALUE]
    if not reading:
        return []
    by_id = {row["id"]: row for row in quarry_db.get_all_books()}
    # title_sort is the column the SQL this replaced ordered by (b.sort);
    # author is the leading author-sort, the MIN(a.sort) of the old query.
    picked = sorted(
        (by_id[bid] for bid in reading if bid in by_id),
        key=lambda row: (row["title_sort"] is None, row["title_sort"] or ""),
    )[:LIMIT]
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "author": min(row["author_sorts"]) if row["author_sorts"] else None,
            "href": "/book/%d" % row["id"],
        }
        for row in picked
    ]


_cache = LibraryCache(_build)


def _shelf():
    try:
        return _cache.get()
    except Exception as ex:
        log.error("Currently-reading shelf unavailable: %s", ex)
        return []


@reading_shelf.app_context_processor
def inject_reading_shelf():
    from .reader_state import continue_reading

    return {"carrel_reading": _shelf(), "carrel_continue": continue_reading()}
