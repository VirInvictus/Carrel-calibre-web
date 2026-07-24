# -*- coding: utf-8 -*-

# Calibre-parity search (Carrel spec 13).
#
# Stock calibre-web has no expression grammar: search_query() lowercases the
# term and hands it to FTS5 as a phrase, so every Calibre-style query matches
# as literal text and returns nothing. Measured against the live library,
# author:"King" returned 0 where Calibre returns 55, and tags:Fic.Fantasy
# returned 0 where Calibre returns 1368.
#
# So the bar evaluates through cquarry's SearchEngine, the same engine wings.py
# already uses for virtual-library expressions. Field prefixes, boolean logic,
# grouping, hierarchical tags, custom columns (#audience:Rin) and vl:
# references all behave as they do in Calibre, including cquarry's documented
# deviations (stdlib re rather than regex, unicodedata rather than ICU,
# anchored tags:).
#
# A bare term keeps Calibre's semantics: substring across title, authors,
# author_sort, series, publisher, tags and comments. That is why a search for
# "King" matches "sorcerer-king" and equally "making" inside a description.
# It is faithful, and it is the cost of parity.

import os

from . import config, logger

log = logger.create()

_cache = {"mtime": None, "db": None}


class SearchError(Exception):
    """A query the grammar could not parse. Carries the engine's own message."""


def _quarry():
    """A cquarry CalibreDB, rebuilt when metadata.db changes.

    cquarry opens its own mode=ro connection, so this never widens the
    read-only guarantee in spec 7.
    """
    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    mtime = os.path.getmtime(dbpath)
    if _cache["mtime"] != mtime:
        from cquarry.db import CalibreDB

        old = _cache.get("db")
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        _cache["db"] = CalibreDB(dbpath)
        _cache["mtime"] = mtime
        log.info("Search engine rebound to metadata.db (mtime %s)", mtime)
    return _cache["db"]


def resolve(term):
    """Query string -> list of book ids. Raises SearchError on a bad query."""
    from cquarry.search import ParseException

    try:
        return list(_quarry().search(term))
    except ParseException as ex:
        raise SearchError(str(ex)) from ex
    except Exception as ex:
        # A malformed query must never 500 the app; surface it as a search
        # error and let the template say so.
        log.error("Search failed for %r: %s", term, ex)
        raise SearchError(str(ex)) from ex
