# -*- coding: utf-8 -*-

# Caching on metadata.db's mtime and library UUID (Carrel spec 7).
#
# Six surfaces (wings, categories, search, series, statistics, the palette)
# all derive something expensive from the library and all invalidate on the
# same signal: the library file changed. Each grew its own copy of the same
# fifteen lines, which meant six places to get the invalidation rule right and
# six places that had drifted on whether a missing metadata.db is a 500 or a
# graceful empty.
#
# This is that rule, once. The library is read-only by contract, so an mtime
# is a sufficient version for in-place edits: nothing in this process can
# change the file, and anything outside it (Calibre) moves the mtime when it
# does. The mtime alone cannot tell a restored *copy* from the original,
# though — `cp -p` reproduces timestamps — so the cache also keys on the
# library's identity UUID from `library_id`, read through cquarry's
# db_uri_ro() contract (0.6.28; the old bare f-string URI silently broke on
# library paths containing '?' or '#'). A bundled copy of the same library
# therefore rebuilds instead of serving the original's cached state after a
# move/restore.

import os
import sqlite3
import threading

from cquarry.helpers import db_uri_ro

from . import config


def library_path():
    """Absolute path to the configured library's metadata.db."""
    return os.path.join(config.config_calibre_dir or "", "metadata.db")


def library_mtime():
    """The library's mtime, or None if it cannot be read.

    Callers that want to degrade rather than fail check for None. Callers that
    genuinely need the library let LibraryCache.get() raise instead.
    """
    try:
        return os.path.getmtime(library_path())
    except OSError:
        return None


def library_uuid():
    """The library's identity UUID, or None when it cannot be read.

    One short-lived mode=ro connection, same as before — but the URI comes
    from cquarry's db_uri_ro() now, whose percent-encoding this path was
    missing (the "deliberately does NOT go through cquarry" note below the
    old code was a stale-install artifact, not architecture: the Phase 4
    venv predated get_library_uuid(), and the stance went with it). Still a
    bare SELECT rather than a full CalibreDB lifecycle because this runs on
    every cache hit; the contract mirrors CalibreDB.get_library_uuid() —
    None on schemas predating the table, degrading to mtime-only
    invalidation exactly as before.
    """
    path = library_path()
    try:
        con = sqlite3.connect(db_uri_ro(path), uri=True)
        try:
            row = con.execute("SELECT uuid FROM library_id LIMIT 1").fetchone()
            return row[0] if row else None
        finally:
            con.close()
    except Exception:
        return None


_quarry_cache = None


def quarry():
    """A shared cquarry CalibreDB, rebuilt when the library moves.

    One open read-only connection for the surfaces that only need a handle
    (cover resolution, analytics, series rollups) — mtime/UUID-keyed like
    every cache here, so a library swap rebuilds it. Modules that own a
    specific engine (carrel_search, page_count, reader_state) keep their own
    caches; this is for the callers that would otherwise open a fresh
    connection per request.
    """
    global _quarry_cache
    if _quarry_cache is None:
        from cquarry.db import CalibreDB

        _quarry_cache = LibraryCache(
            lambda: CalibreDB(library_path()),
            dispose=lambda quarry: quarry.close(),
            label="cquarry",
        )
    return _quarry_cache.get()


class LibraryCache:
    """Memoizes build() until metadata.db's mtime or identity UUID moves.

    build is called with no arguments and may return anything. dispose, if
    given, is called with the previous value once a replacement exists, which
    is how carrel_search closes the sqlite connection it is superseding.
    """

    def __init__(self, build, dispose=None, label=None):
        self._build = build
        self._dispose = dispose
        self._label = label
        self._mtime = None
        self._uuid = None
        self._value = None
        # Phase 12: transitions are serialized. Two threads racing get()
        # could both see a stale mtime and both build (double work, and for
        # carrel_search a disposed-old-value race); the lock makes a rebuild
        # single-file.
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self._get_locked()

    def _get_locked(self):
        mtime = os.path.getmtime(library_path())
        uuid = library_uuid()
        if self._mtime == mtime and self._uuid == uuid:
            return self._value

        # Build before evicting: if the build raises, the previous value is
        # still valid and still cached, rather than the cache being left empty
        # with a live consumer holding a disposed object.
        value = self._build()
        if self._dispose is not None and self._value is not None:
            try:
                self._dispose(self._value)
            except Exception:
                pass
        self._mtime = mtime
        self._uuid = uuid
        self._value = value
        return value

    def invalidate(self):
        """Force the next get() to rebuild. Used by tests."""
        with self._lock:
            self._mtime = None
            self._uuid = None
