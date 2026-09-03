# -*- coding: utf-8 -*-

# Category browser (Carrel spec 4.4).
#
# The library's taxonomy is a dot hierarchy (Fic.Fantasy.Epic), three levels
# deep across 426 tags under Fic, NonFic and Gaming. Stock calibre-web's
# /category/<id> shows only books carrying that exact tag, which is the wrong
# shape here: browsing "Fic.Fantasy" should include everything beneath it.
#
# So counts and membership both roll descendants up, matching cquarry's
# anchored hierarchical semantics (tags:Fic.Fantasy covers Fic.Fantasy and
# anything prefixed Fic.Fantasy.). Membership comes from one pass over the
# tag link table rather than a search per tag, and is cached on metadata.db's
# mtime exactly as wings.py is.

from flask import Blueprint, abort
from flask_babel import gettext as _

from . import logger
from . import quarry_grid
from .library_cache import LibraryCache, quarry
from .render_template import render_title_template
from .usermanagement import login_required_if_no_ano

categories = Blueprint("categories", __name__)
log = logger.create()


def _rollup():
    """tag path -> frozenset of book ids, for every node including implied ones.

    Only leaf tags are assigned in this library: "Fic.Fantasy.Epic.Gods"
    exists, "Fic.Fantasy" does not. The intermediate levels are implied by the
    dot path, so every prefix of every tag becomes a browsable node and
    accumulates its descendants' books. That is the same rule cquarry applies
    for `tags:Fic.Fantasy`, so the browser and the search agree.
    """
    rolled = {}
    # Phase 7 swap: the tag->book pairs come from cquarry's cached rows
    # (every book row carries its tags as a native list) instead of an ORM
    # session query. Same implied-prefix rule as before.
    for book in quarry().get_all_books():
        for name in book["tags"] or []:
            parts = name.split(".")
            for i in range(1, len(parts) + 1):
                rolled.setdefault(".".join(parts[:i]), set()).add(book["id"])
    return {k: frozenset(v) for k, v in rolled.items()}


def _tree(names):
    """Nested {label: {"name": full_or_None, "children": {...}}} from dot paths."""
    root = {}
    for name in names:
        node = root
        parts = name.split(".")
        for i, part in enumerate(parts):
            entry = node.setdefault(part, {"name": None, "children": {}})
            if i == len(parts) - 1:
                entry["name"] = name
            node = entry["children"]
    return root


def _rebuild():
    members = _rollup()
    tree = _tree(sorted(members))
    log.info("Category tree rebuilt: %d tags", len(members))
    # The sidebar's flattened list goes in the cache entry too. It is a walk
    # over every node and every implied prefix, it depends on nothing but the
    # tree and the counts fixed here, and the sidebar renders on every single
    # page: recomputing it per request was the one part of this module that
    # ignored its own cache.
    return tree, members, _as_list(tree, members)


_cache = LibraryCache(_rebuild)


def _build():
    """(tree, members), rebuilt when metadata.db changes."""
    tree, members, _nav = _cache.get()
    return tree, members


def _nav_tree():
    """The sidebar's pre-walked tree, built once per library change."""
    return _cache.get()[2]


def _as_list(node, counts):
    """Nested dicts -> sorted list the template can walk."""
    out = []
    for label, entry in sorted(node.items()):
        name = entry["name"]
        out.append(
            {
                "label": label,
                "name": name,
                "count": len(counts.get(name, ())) if name else 0,
                "children": _as_list(entry["children"], counts),
            }
        )
    return out


@categories.app_context_processor
def inject_categories():
    try:
        return {"category_tree": _nav_tree()}
    except Exception as ex:
        log.error("Category tree unavailable: %s", ex)
        return {"category_tree": []}


@categories.route("/categories/<path:name>", defaults={"page": 1})
@categories.route("/categories/<path:name>/page/<int:page>")
@login_required_if_no_ano
def show_category(name, page):
    try:
        _unused, counts = _build()
    except Exception as ex:
        log.error("Category tree unavailable: %s", ex)
        abort(404)
    ids = counts.get(name)
    if ids is None:
        abort(404)
    entries, pagination = quarry_grid.grid(page, ids)
    return render_title_template(
        "index.html",
        random=None,
        entries=entries,
        pagination=pagination,
        title=_("Category: %(name)s", name=name),
        page="categories",
        category_active=name,
    )
