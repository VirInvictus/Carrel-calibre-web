# -*- coding: utf-8 -*-

# Single-user operation (calibre-web-kanagawa spec 11).
#
# This instance has exactly one reader, so authentication is removed as a
# concept rather than merely bypassed: no credential is ever requested and the
# credential-management paths answer 404.
#
# The owner is authenticated on every request instead of stripping flask-login.
# Upstream has 154 @login_required decorators across 10 modules; rewriting them
# would turn every rebase onto a new upstream tag into a merge conflict, which
# spec section 3 explicitly protects against. Leaving them in place and always
# arriving authenticated makes them pass trivially.
#
# Deleting this module and its two lines in main.py restores stock behaviour.
#
# This is only safe because the server binds localhost (spec 11.3). If it is
# ever exposed to a network again, authentication has to come back with it.

from flask import abort, request

# calibre-web vendors flask-login as cps.cw_login; importing the upstream
# package name fails in this venv.
from .cw_login import current_user, login_user

# Paths that exist only to manage credentials or to manage a user population
# that no longer exists. Compared after stripping a trailing slash, so /login
# and /login/ are both sealed.
#
# /admin/user/<id> is deliberately NOT sealed: it is how the owner edits their
# own locale and sidebar preferences, which is ordinary configuration rather
# than user management.
_SEALED = frozenset((
    "/login",
    "/logout",
    "/register",
    "/admin/user/new",
    "/admin/usertable",
))


def _owner():
    """The account every request runs as: the lowest-numbered admin."""
    from . import constants, ub

    return (
        ub.session.query(ub.User)
        .filter(ub.User.role.op("&")(constants.ROLE_ADMIN) == constants.ROLE_ADMIN)
        .order_by(ub.User.id)
        .first()
    )


def install(app):
    @app.before_request
    def _single_user():
        if request.path.rstrip("/").lower() in _SEALED:
            abort(404)
        if not current_user.is_authenticated:
            owner = _owner()
            if owner is not None:
                # remember=True so the session cookie carries it; the login is
                # re-established per request anyway if the cookie is missing or
                # the session-key check in load_user rejects it.
                login_user(owner, remember=True)
