# -*- coding: utf-8 -*-

# Series awareness (Carrel spec 4.4).
#
# The library holds 804 series and the detail page said nothing about them.
# For a collector the useful facts are: which series is this, where does this
# book sit in it, how much of it do you actually hold, and what is missing.
#
# Gap detection reuses cquarry's detect_series_gaps rather than reimplementing
# it. cquarry is already load-bearing here for search and wings, and two
# copies of the same rule would eventually disagree.

from flask import Blueprint

from . import logger
from .library_cache import LibraryCache, quarry

series_info = Blueprint("series_info", __name__)
log = logger.create()


def _rebuild():
    """series id -> {'name', 'held', 'max', 'gaps'}.

    Phase 7 swap: the data comes from cquarry now — get_entities("series")
    for the id↔name pairing, get_all_series() for the per-series index
    rollups. Same shape the detail page has always consumed; only the
    source moved (Phase 6/9: gap detection already came from cquarry).
    """
    from cquarry.helpers import detect_series_gaps

    quarry_db = quarry()
    ids_by_name = {
        e["name"]: e["id"] for e in quarry_db.get_entities("series")
    }
    out = {}
    for rollup in quarry_db.get_all_series():
        sid = ids_by_name.get(rollup["name"])
        if sid is None:
            continue
        idx = sorted(float(i) for i in rollup["indices"].split(",") if i != "")
        top = max(idx) if idx else None
        gaps = detect_series_gaps(rollup["indices"], top)
        out[sid] = {
            "name": rollup["name"],
            "held": rollup["book_count"],
            # The highest index held, carried as-is. int(top) would truncate
            # a 7.5 to 7 and drop a legitimate index of 0 as falsy, both of
            # which state something the library did not say.
            "max": top,
            "gaps": gaps,
        }

    log.info("Series index rebuilt: %d series", len(out))
    return out


_cache = LibraryCache(_rebuild)


def _build():
    """series id -> {'name', 'held', 'max', 'gaps'}, rebuilt on library change."""
    return _cache.get()


@series_info.app_template_global("carrel_series")
def carrel_series(entry):
    """What the detail page needs to say about this book's series, or None."""
    try:
        if not getattr(entry, "series", None):
            return None
        s = entry.series[0]
        info = _build().get(s.id)
        if not info:
            return None
        index = entry.series_index
        # "max" is deliberately not exposed to the template: it is the highest
        # index held, not the length of the series, and rendering it as
        # "of N" states a fact the library cannot know.
        return {
            "id": s.id,
            "name": info["name"],
            "index": int(index)
            if (index is not None and float(index).is_integer())
            else index,
            "held": info["held"],
            "max": info["max"],
            "gaps": info["gaps"],
        }
    except Exception as ex:
        log.error("Series info unavailable: %s", ex)
        return None
