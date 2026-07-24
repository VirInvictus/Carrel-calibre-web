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

import os

from flask import Blueprint, abort
from flask_babel import gettext as _

from . import calibre_db, config, db, logger
from .render_template import render_title_template
from .usermanagement import login_required_if_no_ano

categories = Blueprint("categories", __name__)
log = logger.create()

_cache = {"mtime": None, "tree": None, "members": None}


def _rollup():
    """tag path -> frozenset of book ids, for every node including implied ones.

    Only leaf tags are assigned in this library: "Fic.Fantasy.Epic.Gods"
    exists, "Fic.Fantasy" does not. The intermediate levels are implied by the
    dot path, so every prefix of every tag becomes a browsable node and
    accumulates its descendants' books. That is the same rule cquarry applies
    for `tags:Fic.Fantasy`, so the browser and the search agree.
    """
    rolled = {}
    rows = (
        calibre_db.session.query(db.Tags.name, db.books_tags_link.c.book)
        .join(db.books_tags_link, db.Tags.id == db.books_tags_link.c.tag)
        .all()
    )
    for name, book in rows:
        parts = name.split(".")
        for i in range(1, len(parts) + 1):
            rolled.setdefault(".".join(parts[:i]), set()).add(book)
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


def _build():
    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    mtime = os.path.getmtime(dbpath)
    if _cache["mtime"] != mtime:
        members = _rollup()
        _cache.update(
            {"mtime": mtime, "members": members, "tree": _tree(sorted(members))}
        )
        log.info("Category tree rebuilt: %d tags", len(members))
    return _cache["tree"], _cache["members"]


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
        tree, counts = _build()
    except Exception as ex:
        log.error("Category tree unavailable: %s", ex)
        return {"category_tree": []}
    return {"category_tree": _as_list(tree, counts)}


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
    entries, random, pagination = calibre_db.fill_indexpage(
        page,
        0,
        db.Books,
        db.Books.id.in_(ids),
        [db.Books.sort],
        True,
        config.config_read_column,
    )
    return render_title_template(
        "index.html",
        random=random,
        entries=entries,
        pagination=pagination,
        title=_("Category: %(name)s", name=name),
        page="categories",
        category_active=name,
    )
