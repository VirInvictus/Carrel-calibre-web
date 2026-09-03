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
from sqlalchemy import text

from . import calibre_db, logger
from .library_cache import LibraryCache

reading_shelf = Blueprint("reading_shelf", __name__)
log = logger.create()

SHELF_VALUE = "Reading"
LIMIT = 12


def _build():
    """[{id, title, author, href}] for the books Calibre marks Reading."""
    try:
        col = calibre_db.session.execute(
            text(
                "SELECT id, normalized FROM custom_columns"
                " WHERE label = 'reading_status'"
            )
        ).fetchone()
    except Exception as ex:
        log.info("reading_status column unreadable: %s", ex)
        return []
    if not col:
        return []
    cid, normalized = col[0], col[1]
    if normalized:
        sql = (
            "SELECT b.id, b.title, MIN(a.sort) AS author"
            " FROM books b"
            " JOIN books_authors_link bal ON bal.book = b.id"
            " JOIN authors a ON a.id = bal.author"
            " JOIN books_custom_column_%d_link l ON l.book = b.id"
            " JOIN custom_column_%d v ON v.id = l.value"
            " WHERE v.value = :v"
            " GROUP BY b.id, b.title ORDER BY b.sort" % (cid, cid)
        )
    else:
        sql = (
            "SELECT b.id, b.title, MIN(a.sort) AS author"
            " FROM books b"
            " JOIN books_authors_link bal ON bal.book = b.id"
            " JOIN authors a ON a.id = bal.author"
            " JOIN custom_column_%d v ON v.book = b.id"
            " WHERE v.value = :v"
            " GROUP BY b.id, b.title ORDER BY b.sort" % cid
        )
    try:
        rows = calibre_db.session.execute(text(sql), {"v": SHELF_VALUE}).fetchall()
    except Exception as ex:
        log.info("currently-reading query failed: %s", ex)
        return []
    return [
        {"id": r[0], "title": r[1], "author": r[2], "href": "/book/%d" % r[0]}
        for r in rows[:LIMIT]
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
    return {"carrel_reading": _shelf()}
