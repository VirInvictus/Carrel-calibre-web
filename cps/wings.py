# -*- coding: utf-8 -*-

# Wings: Calibre virtual libraries as read-only browse sections
# (Carrel spec 8). Wing expressions live in metadata.db's
# preferences table and are evaluated by CalibreQuarry's stdlib port of
# Calibre's search grammar (including vl: cross-references, so the
# self-referential Unsorted wing parses). cquarry opens its own mode=ro
# connection; results are cached keyed on metadata.db's mtime, so any
# library change invalidates on the next request.

from flask import Blueprint, abort
from flask_babel import gettext as _

from . import calibre_db, config, db, logger
from .library_cache import LibraryCache, library_path
from .render_template import render_title_template
from .usermanagement import login_required_if_no_ano

wings = Blueprint("wings", __name__)
log = logger.create()


def _resolve_wings():
    from cquarry.db import CalibreDB

    with CalibreDB(library_path()) as quarry:
        names = quarry.get_virtual_libraries()
        # Mirror the Calibre GUI's own sidebar (cquarry 1.1): drop libraries
        # the user hid and follow the stored tab order; anything unknown to
        # that state keeps alphabetical order after the known ones.
        ui = quarry.get_vl_ui_state()
        hidden = {str(h).lower() for h in ui.get("hidden", [])}
        order = ui.get("order") or {}

        def sort_key(name):
            for key, pos in order.items():
                if str(key).lower() == name.lower():
                    try:
                        return (0, float(pos), name.lower())
                    except (TypeError, ValueError):
                        return (1, 0.0, name.lower())
            return (1, 0.0, name.lower())

        resolved = {
            name: frozenset(quarry.resolve_vl(name))
            for name in sorted(
                (n for n in names if n.lower() not in hidden), key=sort_key
            )
        }
    log.info("Wings cache rebuilt: %d wings", len(resolved))
    return resolved


_cache = LibraryCache(_resolve_wings)


def _wing_ids():
    """Wing name -> frozenset of book ids, rebuilt when metadata.db changes."""
    return _cache.get()


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
