# -*- coding: utf-8 -*-

# Wings: Calibre virtual libraries as read-only browse sections
# (calibre-web-kanagawa spec 8). Wing expressions live in metadata.db's
# preferences table and are evaluated by CalibreQuarry's stdlib port of
# Calibre's search grammar (including vl: cross-references, so the
# self-referential Unsorted wing parses). cquarry opens its own mode=ro
# connection; results are cached keyed on metadata.db's mtime, so any
# library change invalidates on the next request.

import os

from flask import Blueprint, abort
from flask_babel import gettext as _

from . import calibre_db, config, db, logger
from .render_template import render_title_template
from .usermanagement import login_required_if_no_ano

wings = Blueprint("wings", __name__)
log = logger.create()

_cache = {"mtime": None, "wings": None}


def _wing_ids():
    """Wing name -> frozenset of book ids, rebuilt when metadata.db changes."""
    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    mtime = os.path.getmtime(dbpath)
    if _cache["mtime"] != mtime:
        from cquarry.db import CalibreDB

        with CalibreDB(dbpath) as quarry:
            resolved = {
                name: frozenset(quarry.resolve_vl(name))
                for name in quarry.get_virtual_libraries()
            }
        _cache["mtime"] = mtime
        _cache["wings"] = resolved
        log.info("Wings cache rebuilt: %d wings", len(resolved))
    return _cache["wings"]


@wings.app_context_processor
def inject_wings():
    try:
        resolved = _wing_ids()
    except Exception as ex:
        log.error("Wings unavailable: %s", ex)
        return {"wings_list": []}
    return {
        "wings_list": [
            {"name": name, "count": len(ids)} for name, ids in resolved.items()
        ]
    }


@wings.route("/wings/<path:name>", defaults={"page": 1})
@wings.route("/wings/<path:name>/page/<int:page>")
@login_required_if_no_ano
def show_wing(name, page):
    try:
        ids = _wing_ids().get(name)
    except Exception as ex:
        log.error("Wings unavailable: %s", ex)
        ids = None
    if ids is None:
        abort(404)
    db_filter = db.Books.id.in_(ids)
    entries, random, pagination = calibre_db.fill_indexpage(
        page, 0, db.Books, db_filter, [db.Books.sort], True, config.config_read_column
    )
    return render_title_template(
        "index.html",
        random=random,
        entries=entries,
        pagination=pagination,
        title=_("Wing: %(name)s", name=name),
        page="wings",
        wing_active=name,
    )
