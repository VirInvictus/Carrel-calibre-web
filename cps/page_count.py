# -*- coding: utf-8 -*-

# Native page counts on the detail page (cquarry 1.3).
#
# Calibre maintains per-book page counts in its own `books_pages_link` table
# (populated by the CountPages integration); cquarry reads it natively and
# falls back to a `#pages` custom column on older schemas. The detail page
# asks one question — how long is this book? — so this module answers that
# and nothing more, following the reader_state pattern: a Jinja template
# global that either answers or says None, never 500s.

from flask import Blueprint  # noqa: E402

from . import logger
from .library_cache import LibraryCache, library_path

log = logger.create()

# A blueprint only so Flask gives us app_template_global registration; it has
# no routes of its own.
page_count = Blueprint("page_count", __name__)


def _rebuild():
    from cquarry.db import CalibreDB

    quarry = CalibreDB(library_path())
    log.info("Page-count engine rebound to metadata.db")
    return quarry


def _dispose(quarry):
    quarry.close()


_cache = LibraryCache(_rebuild, dispose=_dispose)


def _quarry():
    return _cache.get()


@page_count.app_template_global("carrel_page_count")
def carrel_page_count(book_id):
    """The book's native page count, or None when the library doesn't know."""
    try:
        return _quarry().field(book_id, "pages")
    except Exception as ex:
        log.error("Page count unavailable for book %s: %s", book_id, ex)
        return None
