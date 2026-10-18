# -*- coding: utf-8 -*-

# Reader state on the detail page: e-reader highlights and reading progress
# (cquarry 1.1 extractors).
#
# Calibre's wireless drivers record highlights/bookmarks in `annotations` and
# per-device positions in `last_read_positions`. The reading room cares about
# exactly two questions — how far into this book am I, and what have I marked
# — so this module answers those two and nothing more.
#
# Exposed as a Jinja template global (`carrel_reader_state`) following the
# series_info pattern: the template asks, this module either answers or says
# None, and a broken extractor degrades to "no state shown" instead of a 500.

from . import logger
from .library_cache import LibraryCache, library_path

log = logger.create()

# A blueprint only so Flask gives us app_template_global registration; it has
# no routes of its own.
from flask import Blueprint  # noqa: E402

reader_state = Blueprint("reader_state", __name__)


def _rebuild():
    from cquarry.db import CalibreDB

    quarry = CalibreDB(library_path())
    log.info("Reader-state engine rebound to metadata.db")
    return quarry


def _dispose(quarry):
    quarry.close()


_cache = LibraryCache(_rebuild, dispose=_dispose)


def _quarry():
    return _cache.get()


@reader_state.app_template_global("carrel_reader_state")
def carrel_reader_state(book_id):
    """Highlights and latest progress for one book id, or None.

    Returns {'annotations': [...], 'progress': float|None, 'device': str|None}.
    Progress is the most recent pos_frac across devices (epoch wins).
    """
    try:
        quarry = _quarry()
        annotations = quarry.get_annotations(book_id)
        positions = quarry.get_last_read_positions(book_id)
    except Exception as ex:
        log.error("Reader state unavailable for book %s: %s", book_id, ex)
        return None

    progress = None
    device = None
    if positions:
        latest = max(positions, key=lambda r: r.get("epoch") or 0)
        frac = latest.get("pos_frac")
        if frac is not None:
            progress = float(frac)
            device = latest.get("device")

    if not annotations and progress is None:
        return None
    return {
        "annotations": annotations,
        "progress": progress,
        "device": device,
    }


def latest_position(book_id, book_format=None):
    """The most recent reading position's CFI for one book, or None.

    Feeds the browser reader's position sync: when the reader has no
    bookmark of its own, the device-recorded position opens the book.
    Rows whose format matches win; otherwise the latest row overall
    answers. Never raises: a broken extractor costs the position, not
    the reader page.
    """
    try:
        positions = _quarry().get_last_read_positions(book_id)
    except Exception as ex:
        log.error("Reading positions unavailable for book %s: %s", book_id, ex)
        return None
    if not positions:
        return None
    fmt = (book_format or "").upper()
    matching = [r for r in positions if (r.get("format") or "").upper() == fmt]
    pool = matching or positions
    return max(pool, key=lambda r: r.get("epoch") or 0).get("cfi") or None
