# -*- coding: utf-8 -*-

# Route trimming for the smallscope instance (Carrel spec 6.2).
# Blueprints stay registered so url_for() keeps resolving wherever a template
# or script still references them; their routes simply answer 404. This keeps
# the diff against upstream small and rebase-friendly.

from flask import abort


def _disable(blueprint):
    @blueprint.before_request
    def _disabled():
        abort(404)


def trim(*blueprints):
    for blueprint in blueprints:
        if blueprint is not None:
            _disable(blueprint)


def read_column_is_enum(column_id):
    # True when the linked read column is normalized (enumeration), i.e. has
    # no direct 'book' attribute the way bool/int/float/datetime columns do.
    # Only bool and enumeration pass the admin filter, so normalized == enum.
    from . import db

    cc_class = db.cc_classes.get(column_id)
    return cc_class is not None and not hasattr(cc_class, "book")
