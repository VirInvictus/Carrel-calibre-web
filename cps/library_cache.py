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
#
# Delivery is stale-while-revalidate (0.6.47). Calibre desktop holds
# metadata.db open and touches its mtime every few seconds, which under the
# old rebuild-inline-on-change rule meant the caches were never warm: every
# request re-paid the full derivation (wings alone was ~10s of CPU on this
# library), and because a rebuild is CPU-bound it froze the whole server
# loop while it ran. The rule now is: the first build is inline and locked;
# after that, a moved signature serves the last good value immediately and
# re-derives in the background, throttled so the cache does not chase a
# writer that never settles — a rebuild starts only once the signature has
# held steady for _REVALIDATE_QUIET_SECONDS, or when the served value is
# older than _STALE_MAX_SECONDS regardless of churn. When builds succeed,
# staleness is bounded at about two minutes; a persistently FAILING build
# keeps serving the last good value and logs each retry instead (the
# surfaces' degrade conventions only cover an unreadable library, which
# still raises). Rebuilds still run one at a time per cache, and the
# superseded value is kept one generation before its dispose runs, so a
# request that took the old value is not left holding a closed handle
# while the background refresh swaps underneath it (the cover route
# additionally guards its handle use).
#
# The threading contract that makes the background rebuild safe (0.6.47,
# code-review finding): a sqlite3 connection is bound to the thread that
# opened it, so a cache whose VALUE embeds a live CalibreDB must never
# hand one across threads. Pass background=False for those (the shared
# quarry handle, the search engine, the detail-page engines) — they
# rebuild inline on the request thread, which is cheap because
# constructing CalibreDB is. A background cache must return PLAIN DATA
# derived inside its build from a handle the build opened and closed
# itself (the wings idiom), never the shared quarry() and never the ORM.

import os
import sqlite3
import threading
import time

from cquarry.helpers import db_uri_ro

from . import config
from . import logger

log = logger.create()

# Revalidation throttle. A rebuild starts only when the library signature
# has been stable this long (the writer has settled) ...
_REVALIDATE_QUIET_SECONDS = 10.0
# ... or the served value has been stale this long no matter what the
# writer is doing (staleness stays bounded during endless churn).
_STALE_MAX_SECONDS = 120.0
# Floor between background rebuild attempts, so a failing or perpetually
# superseded build cannot hot-loop.
_REBUILD_MIN_INTERVAL = 20.0


def library_path():
    """Absolute path to the configured library's metadata.db."""
    return os.path.join(config.config_calibre_dir or "", "metadata.db")


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


def _signature():
    """(mtime, uuid) for the library right now."""
    return os.path.getmtime(library_path()), library_uuid()


def _signature_for_request():
    """The library signature, probed at most once per request.

    The context processors and the routes they serve each probed on every
    cache hit: an os.stat plus a fresh sqlite connection for the UUID,
    six-odd times per page render. The first probe now answers for the
    whole request, which also gives one request one consistent view of
    the library. Outside a request context, every get() probes directly.
    """
    try:
        from flask import g, has_request_context

        if has_request_context():
            signature = getattr(g, "_carrel_library_signature", None)
            if signature is None:
                signature = _signature()
                g._carrel_library_signature = signature
            return signature
    except RuntimeError:
        pass
    return _signature()


_quarry_cache = None


def quarry():
    """A shared cquarry CalibreDB, rebuilt when the library moves.

    One open read-only connection for the surfaces that only need a handle
    (cover resolution, analytics, series rollups, the OPDS entity feeds) —
    mtime/UUID-keyed like
    every cache here, so a library swap rebuilds it. Modules that own a
    specific engine (carrel_search, page_count, reader_state) keep their own
    caches; this is for the callers that would otherwise open a fresh
    connection per request.
    """
    global _quarry_cache
    if _quarry_cache is None:
        from cquarry.db import CalibreDB

        # background=False: the cached value is the live handle itself, and
        # a sqlite3 connection may not cross threads (see the module
        # docstring). Inline is cheap — constructing CalibreDB is ~2ms.
        _quarry_cache = LibraryCache(
            lambda: CalibreDB(library_path()),
            dispose=lambda quarry: quarry.close(),
            label="cquarry",
            background=False,
        )
    return _quarry_cache.get()


class LibraryCache:
    """Memoizes build() until metadata.db's mtime or identity UUID moves.

    The first get() builds inline, under the lock. Once a value exists, a
    moved signature serves the stale value right away and re-derives in a
    background thread (one at a time, throttled: see the module constants).
    A caller that must have fresh data calls flush(), which rebuilds
    inline; invalidate() discards the value entirely so the next get() is a
    cold build. The signature probe raises when the library itself cannot
    be read — degradation to 503/empty is the surfaces' own convention and
    a vanished library is never papered over with stale data.

    dispose, if given, is called with a superseded value once a
    replacement has been in service for one full generation, which is how
    carrel_search closes the sqlite connection it is superseding without
    pulling it out from under a request that took the old value moments
    before the swap.
    """

    def __init__(self, build, dispose=None, label=None, background=True):
        self._build = build
        self._dispose = dispose
        self._label = label
        # True (plain-data builds only, see the module docstring): a moved
        # signature serves the stale value and re-derives on a background
        # thread. False (handle-embedding caches): a moved signature
        # rebuilds inline on the request thread, exactly as before 0.6.47,
        # and build failures propagate to the surface's degrade convention.
        self._background = background
        self._mtime = None
        self._uuid = None
        self._value = None
        self._built_at = None
        # Phase 12: transitions are serialized. Two threads racing get()
        # could both see a stale mtime and both build (double work, and for
        # carrel_search a disposed-old-value race); the lock makes a rebuild
        # single-file.
        self._lock = threading.Lock()
        # Stale-while-revalidate state (0.6.47). _refreshing is the
        # single-flight flag for the background rebuild; _observed_* tracks
        # how long the current signature has held (the quiet window);
        # _last_build_at throttles consecutive attempts; _retired holds
        # superseded values for one generation before disposal.
        self._refreshing = False
        self._observed_sig = None
        self._observed_since = None
        self._last_build_at = None
        self._retired = []

    @property
    def built_at(self):
        """Wall-clock time of the build behind the current value, or None.

        Cache-busters key on this (the palette index URL), so a browser
        refetches only when a rebuild actually changed the content, not on
        every library mtime touch.
        """
        return self._built_at

    def get(self):
        with self._lock:
            return self._get_locked()

    def _get_locked(self):
        mtime, uuid = _signature_for_request()
        signature = (mtime, uuid)
        now = time.monotonic()

        if signature == (self._mtime, self._uuid):
            self._observed_sig = signature
            if self._observed_since is None:
                self._observed_since = now
            return self._value

        if self._observed_sig != signature:
            self._observed_sig = signature
            self._observed_since = now

        if self._value is None:
            # Cold: nothing to serve stale, build inline as always.
            return self._build_inline_locked(signature)

        if not self._background:
            # A handle-embedding cache: rebuild inline (cheap) so the value
            # is built and used on the same thread; failures propagate to
            # the surface's own degrade convention.
            return self._build_inline_locked(signature)

        # Warm but superseded: serve the last good value; re-derive in the
        # background once the writer settles (or staleness maxes out),
        # one attempt at a time.
        quiet = now - self._observed_since >= _REVALIDATE_QUIET_SECONDS
        maxed = now - (self._last_build_at or 0.0) >= _STALE_MAX_SECONDS
        throttled = self._last_build_at is not None and (
            now - self._last_build_at < _REBUILD_MIN_INTERVAL
        )
        if not self._refreshing and not throttled and (quiet or maxed):
            self._refreshing = True
            self._last_build_at = now
            try:
                threading.Thread(
                    target=self._refresh,
                    args=(signature, (self._mtime, self._uuid)),
                    daemon=True,
                ).start()
            except Exception:
                # start() itself failed (thread exhaustion): un-strand the
                # flag and keep serving stale; the throttle retries later.
                self._refreshing = False
        return self._value

    def _build_inline_locked(self, signature):
        value = self._build()
        self._retire_locked()
        self._mtime, self._uuid = signature
        self._built_at = time.time()
        self._last_build_at = time.monotonic()
        self._value = value
        return value

    def _refresh(self, signature, prev_signature):
        """Background re-derivation. The stale value stays in service if the
        build fails; the next quiet-or-maxed window retries."""
        try:
            value = self._build()
        except Exception as ex:
            log.error(
                "Library cache %s revalidation failed; serving the previous value: %s",
                self._label or "<unnamed>",
                ex,
            )
            with self._lock:
                self._refreshing = False
            return
        with self._lock:
            self._refreshing = False
            if (self._mtime, self._uuid) != prev_signature:
                # The generation we started from is gone: a flush() (or an
                # inline rebuild) installed something newer while we
                # built. Keep it and drop ours, disposing what a
                # dispose-aware owner can.
                if self._dispose is not None:
                    try:
                        self._dispose(value)
                    except Exception:
                        pass
                return
            self._retire_locked()
            self._mtime, self._uuid = signature
            self._built_at = time.time()
            self._last_build_at = time.monotonic()
            self._value = value

    def _retire_locked(self):
        """Park the superseded value; dispose it one generation later.

        Requests take the value out of the cache and then use it; disposing
        at swap time could close a handle (or engine) a request is still
        reading. One generation of grace covers that honestly cheaply.
        """
        if self._value is not None:
            self._retired.append(self._value)
        while len(self._retired) > 1:
            old = self._retired.pop(0)
            if self._dispose is not None:
                try:
                    self._dispose(old)
                except Exception:
                    pass

    def flush(self):
        """Rebuild inline right now if the signature moved; else a no-op.

        The synchronous escape hatch for tests and for callers that must
        answer from fresh data, kept out of get() so page renders never
        block on a derivation.
        """
        with self._lock:
            signature = _signature()
            if signature == (self._mtime, self._uuid):
                return self._value
            return self._build_inline_locked(signature)

    def invalidate(self):
        """Discard the cached value entirely: the next get() is a cold build.

        Used by tests (and by callers that know the derivation itself went
        stale in a way a signature cannot describe). The superseded value,
        if any, is parked for delayed disposal like any other generation.
        """
        with self._lock:
            self._mtime = None
            self._uuid = None
            self._built_at = None
            if self._value is not None:
                self._retired.append(self._value)
            self._value = None
