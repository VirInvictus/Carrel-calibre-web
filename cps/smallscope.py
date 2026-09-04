# -*- coding: utf-8 -*-

# Route trimming for the smallscope instance (Carrel spec 6.2).
# Blueprints stay registered so url_for() keeps resolving wherever a template
# or script still references them; their routes simply answer 404. This keeps
# the diff against upstream small and rebase-friendly.

from flask import abort, request

# Browse surfaces cut in Phase 8 (Carrel spec 4.4). These are not separate
# blueprints: web.py registers them dynamically as /<data>/<sort_param>, so
# they are sealed by path prefix rather than by trim(). Hot ranks by download
# count, which is meaningless on a single-user instance.
# /advsearch goes too (spec 13): its form builds SQLAlchemy filters with
# ilike substring semantics, which disagree with the engine the search bar
# now uses. One grammar or none. The bar strictly subsumes the form:
# `tags:Fic.Fantasy AND rating:>=4 AND #audience:Rin` is not expressible
# in it at all.
_SEALED_PREFIXES = (
    "/hot", "/rated", "/discover", "/advsearch",
    "/table", "/ajax/listbooks", "/ajax/table_settings",
)


def _disable(blueprint):
    @blueprint.before_request
    def _disabled():
        abort(404)


def trim(*blueprints):
    for blueprint in blueprints:
        if blueprint is not None:
            _disable(blueprint)


def seal_browse_surfaces(app):
    @app.before_request
    def _sealed():
        # Normalized: /Hot/ is the same route as /hot/, and a capitalized
        # bypass is not a feature (Phase 12).
        path = request.path.rstrip("/").lower()
        for prefix in _SEALED_PREFIXES:
            prefix = prefix.lower()
            if path == prefix or path.startswith(prefix + "/"):
                abort(404)


def read_column_is_enum(column_id):
    # True when the linked read column is normalized (enumeration), i.e. has
    # no direct 'book' attribute the way bool/int/float/datetime columns do.
    # Only bool and enumeration pass the admin filter, so normalized == enum.
    from . import db

    cc_class = db.cc_classes.get(column_id)
    return cc_class is not None and not hasattr(cc_class, "book")
