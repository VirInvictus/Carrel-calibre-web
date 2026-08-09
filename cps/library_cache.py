# -*- coding: utf-8 -*-

# Caching on metadata.db's mtime (Carrel spec 7).
#
# Six surfaces (wings, categories, search, series, statistics, the palette)
# all derive something expensive from the library and all invalidate on the
# same signal: the library file changed. Each grew its own copy of the same
# fifteen lines, which meant six places to get the invalidation rule right and
# six places that had drifted on whether a missing metadata.db is a 500 or a
# graceful empty.
#
# This is that rule, once. The library is read-only by contract, so an mtime
# is a sufficient version: nothing in this process can change the file, and
# anything outside it (Calibre) moves the mtime when it does.

import os

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


class LibraryCache:
    """Memoizes build() until metadata.db's mtime moves.

    build is called with no arguments and may return anything. dispose, if
    given, is called with the previous value once a replacement exists, which
    is how carrel_search closes the sqlite connection it is superseding.
    """

    def __init__(self, build, dispose=None, label=None):
        self._build = build
        self._dispose = dispose
        self._label = label
        self._mtime = None
        self._value = None

    def get(self):
        mtime = os.path.getmtime(library_path())
        if self._mtime == mtime:
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
        self._value = value
        return value

    def invalidate(self):
        """Force the next get() to rebuild. Used by tests."""
        self._mtime = None
