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
# client-side over the full set, which is what makes it feel instant, and there
# is exactly one reader to serve it to (spec 11).

import json

from flask import Blueprint, Response

from . import calibre_db, db, logger
from .library_cache import LibraryCache, library_mtime
from .usermanagement import login_required_if_no_ano

palette = Blueprint("palette", __name__)
log = logger.create()


def _entries():
    """[{t: title, g: group, h: href}] for everything worth jumping to."""
    rows = []

    # Fixed destinations first: they are few and should rank early on ties.
    # calibre-web has two shapes and they are easy to confuse. The overview
    # pages are bare (/author, /series), while an individual entity is
    # /<data>/<sort_param>/<id>. Getting that wrong does not 404: the id lands
    # in sort_param and book_id silently defaults to 1, so every author link
    # opened whoever author 1 happens to be.
    for title, href in (
        ("Books", "/"),
        ("Authors", "/author"),
        ("Series", "/series"),
        ("Categories", "/category"),
        ("Publishers", "/publisher"),
        ("Languages", "/language"),
        ("Ratings", "/ratings"),
        ("File formats", "/formats"),
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
                "h": "/author/stored/%d" % author.id,
            }
        )
    for series in session.query(db.Series).all():
        rows.append(
            {"t": series.name, "g": "series", "h": "/series/stored/%d" % series.id}
        )
    # Categories jump to Carrel's roll-up browser rather than stock
    # calibre-web's /category/stored/<id>: the sidebar tree already goes there,
    # and one concept should not have two destinations. For a leaf tag the two
    # show the same books anyway, since a leaf's roll-up is itself.
    #
    # Only leaf tags are indexed, which is what `tags` holds. The implied
    # intermediate nodes (Fic.Fantasy) stay reachable through the tree and not
    # through Ctrl-K; indexing them too would grow the payload for a set of
    # destinations that are one click away in the sidebar.
    for tag in session.query(db.Tags).all():
        rows.append(
            {"t": tag.name, "g": "category", "h": "/categories/%s" % quote(tag.name)}
        )

    return rows


def _body():
    rows = _entries()
    log.info("Palette index rebuilt: %d entries", len(rows))
    return "window.PALETTE=%s;" % json.dumps(
        rows, ensure_ascii=False, separators=(",", ":")
    )


_cache = LibraryCache(_body)


@palette.route("/palette-data.js")
@login_required_if_no_ano
def palette_data():
    try:
        body = _cache.get()
    except Exception as ex:
        # palette.js already treats an empty index as "no palette" and stands
        # down, so an unreachable library costs the shortcut and nothing else.
        # This used to raise out of an unguarded getmtime.
        log.error("Palette index unavailable: %s", ex)
        body = "window.PALETTE=[];"
    # The URL carries metadata.db's mtime (see palette_version below), so a
    # given URL's content can never change. Without this the browser reparses
    # ~390 KB of index on every page load.
    return Response(
        body,
        mimetype="application/javascript",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


@palette.app_context_processor
def inject_palette_version():
    """Cache-buster for the palette index URL, keyed on the library's mtime."""
    mtime = library_mtime()
    return {"palette_version": int(mtime) if mtime is not None else 0}
