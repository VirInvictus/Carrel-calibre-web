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

import os

from flask import Blueprint

from . import calibre_db, config, db, logger

series_info = Blueprint("series_info", __name__)
log = logger.create()

_cache = {"mtime": None, "series": None}


def _build():
    """series id -> {'name', 'held', 'max', 'gaps', 'indices'}."""
    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    mtime = os.path.getmtime(dbpath)
    if _cache["mtime"] == mtime:
        return _cache["series"]

    from cquarry.helpers import detect_series_gaps

    rows = (
        calibre_db.session.query(db.Series.id, db.Series.name, db.Books.series_index)
        .join(db.books_series_link, db.Series.id == db.books_series_link.c.series)
        .join(db.Books, db.Books.id == db.books_series_link.c.book)
        .all()
    )
    by_id = {}
    for sid, name, index in rows:
        entry = by_id.setdefault(sid, {"name": name, "indices": []})
        if index is not None:
            entry["indices"].append(float(index))

    out = {}
    for sid, entry in by_id.items():
        idx = sorted(entry["indices"])
        top = max(idx) if idx else None
        gaps = detect_series_gaps(",".join(str(i) for i in idx), top)
        out[sid] = {
            "name": entry["name"],
            "held": len(idx),
            "max": int(top) if top else None,
            "gaps": gaps,
        }

    _cache.update({"mtime": mtime, "series": out})
    log.info("Series index rebuilt: %d series", len(out))
    return out


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
            "index": int(index) if index and float(index).is_integer() else index,
            "held": info["held"],
            "max": info["max"],
            "gaps": info["gaps"],
        }
    except Exception as ex:
        log.error("Series info unavailable: %s", ex)
        return None
