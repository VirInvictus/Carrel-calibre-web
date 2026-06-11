# -*- coding: utf-8 -*-

# Route trimming for the smallscope instance (calibre-web-kanagawa spec 6.2).
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
