# -*- coding: utf-8 -*-

# Command palette data (Carrel spec 4.4).
#
# Ctrl-K opens a fuzzy jumper over every navigable thing in the library:
# wings, authors, series, categories, and the fixed pages. This module emits
# that index as a JavaScript file so the palette script can stay a static
# asset with no fetch and no API surface.
#
# Ported in shape from Brandon's Athenaeum static site, which builds the same
# index at generation time. Here it is built from metadata.db instead, cached
# on the database's mtime exactly as wings.py does, so any library edit
# invalidates it on the next request.
#
# The payload is deliberately whole rather than paged: the fuzzy match runs
# client-side over the full set, which is what makes it feel instant, and the
# instance is localhost single-user.

import json
import os

from flask import Blueprint, Response

from . import calibre_db, config, db, logger
from .usermanagement import login_required_if_no_ano

palette = Blueprint("palette", __name__)
log = logger.create()

_cache = {"mtime": None, "body": None}


def _entries():
    """[{t: title, g: group, h: href}] for everything worth jumping to."""
    rows = []

    # Fixed destinations first: they are few and should rank early on ties.
    for title, href in (
        ("Books", "/"),
        ("Authors", "/author/stored"),
        ("Series", "/series/stored"),
        ("Categories", "/category/stored"),
        ("Publishers", "/publisher/stored"),
        ("Languages", "/language/stored"),
        ("Ratings", "/rating/stored"),
        ("File formats", "/format/stored"),
        ("Read Books", "/read/stored"),
        ("Unread Books", "/unread/stored"),
        ("Archived Books", "/archived/stored"),
        ("Books List", "/table"),
        ("Statistics", "/statistics"),
    ):
        rows.append({"t": title, "g": "page", "h": href})

    from urllib.parse import quote

    from .wings import _wing_ids

    for name in _wing_ids():
        rows.append({"t": name, "g": "wing", "h": "/wings/%s" % quote(name)})

    session = calibre_db.session
    for author in session.query(db.Authors).all():
        rows.append(
            {
                "t": author.name.replace("|", ","),
                "g": "author",
                "h": "/author/%d" % author.id,
            }
        )
    for series in session.query(db.Series).all():
        rows.append({"t": series.name, "g": "series", "h": "/series/%d" % series.id})
    for tag in session.query(db.Tags).all():
        rows.append({"t": tag.name, "g": "category", "h": "/category/%d" % tag.id})

    return rows


@palette.route("/palette-data.js")
@login_required_if_no_ano
def palette_data():
    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    mtime = os.path.getmtime(dbpath)
    if _cache["mtime"] != mtime:
        rows = _entries()
        _cache["body"] = "window.PALETTE=%s;" % json.dumps(
            rows, ensure_ascii=False, separators=(",", ":")
        )
        _cache["mtime"] = mtime
        log.info("Palette index rebuilt: %d entries", len(rows))
    # The URL carries metadata.db's mtime (see palette_version below), so a
    # given URL's content can never change. Without this the browser reparses
    # ~390 KB of index on every page load.
    return Response(
        _cache["body"],
        mimetype="application/javascript",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


@palette.app_context_processor
def inject_palette_version():
    """Cache-buster for the palette index URL, keyed on the library's mtime."""
    try:
        dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
        return {"palette_version": int(os.path.getmtime(dbpath))}
    except Exception:
        return {"palette_version": 0}
