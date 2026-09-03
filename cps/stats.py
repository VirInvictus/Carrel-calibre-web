# -*- coding: utf-8 -*-

# Library statistics (Carrel spec 12).
#
# Headless metric functions: each returns plain data, none of them formats,
# and none of them knows about HTML. Everything is read straight from
# metadata.db through the app's own mode=ro connection (spec 7), so this can
# never write to the library.
#
# Which axes get a chart and which get a one-line readout is decided by the
# data, not by symmetry: this library is 98% To Read, 96% one source, and only
# 2% rated, so those would be charts of a single slice. They are readouts.
# See spec 12.1 for the split and the counts that justify it.

from flask import Blueprint, abort
from flask_babel import gettext as _
from sqlalchemy import text

from . import calibre_db, logger
from .library_cache import LibraryCache
from .render_template import render_title_template
from .usermanagement import login_required_if_no_ano

statistics = Blueprint("statistics", __name__)
log = logger.create()

TOP_N = 12


def _rows(sql, **params):
    return calibre_db.session.execute(text(sql), params).fetchall()


def _totals():
    one = lambda sql: _rows(sql)[0][0]  # noqa: E731
    return {
        "books": one("SELECT count(*) FROM books"),
        "authors": one("SELECT count(*) FROM authors"),
        "series": one("SELECT count(*) FROM series"),
        "tags": one("SELECT count(*) FROM tags"),
        "publishers": one("SELECT count(*) FROM publishers"),
        "formats": one("SELECT count(DISTINCT format) FROM data"),
    }


def _by_decade():
    rows = _rows(
        "SELECT (CAST(strftime('%Y', pubdate) AS INTEGER) / 10) * 10 AS dec,"
        " count(*) FROM books WHERE pubdate IS NOT NULL"
        " AND CAST(strftime('%Y', pubdate) AS INTEGER) > 1400"
        " GROUP BY dec ORDER BY dec"
    )
    # Everything before 1900 is a long tail of one- and two-book decades
    # (1580s: 1, 1590s: 4, ...). Charted individually it is forty rows of
    # noise that flattens the distribution that actually exists. Bucketed, the
    # shape of the library is legible and nothing is hidden: the bucket is
    # labelled and carries its own count.
    early = sum(n for d, n in rows if d < 1900)
    out = [{"label": "%ss" % d, "value": n} for d, n in rows if d >= 1900]
    if early:
        out.insert(0, {"label": "pre-1900", "value": early})
    return out


def _formats():
    rows = _rows("SELECT format, count(*) c FROM data GROUP BY format ORDER BY c DESC")
    return [{"label": f, "value": n} for f, n in rows]


def _genre_spine():
    """Top-level tag families, counted over books not tags."""
    rows = _rows(
        "SELECT substr(t.name, 1, CASE WHEN instr(t.name, '.') = 0"
        " THEN length(t.name) ELSE instr(t.name, '.') - 1 END) AS fam,"
        " count(DISTINCT l.book) c"
        " FROM tags t JOIN books_tags_link l ON l.tag = t.id"
        " GROUP BY fam ORDER BY c DESC"
    )
    return [{"label": f, "value": n} for f, n in rows]


def _top(table, link, col, label_col="name"):
    rows = _rows(
        "SELECT x.%s, count(DISTINCT l.book) c FROM %s x"
        " JOIN %s l ON l.%s = x.id GROUP BY x.id ORDER BY c DESC, x.%s LIMIT :n"
        % (label_col, table, link, col, label_col),
        n=TOP_N,
    )
    return [{"label": (v or "").replace("|", ","), "value": n} for v, n in rows]


def _hour_histogram():
    rows = _rows(
        "SELECT CAST(strftime('%H', timestamp) AS INTEGER) h, count(*)"
        " FROM books GROUP BY h ORDER BY h"
    )
    counts = {int(h): n for h, n in rows if h is not None}
    return [{"label": "%02d" % h, "value": counts.get(h, 0)} for h in range(24)]


def _weekday_histogram():
    rows = _rows(
        "SELECT CAST(strftime('%w', timestamp) AS INTEGER) d, count(*)"
        " FROM books GROUP BY d ORDER BY d"
    )
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    counts = {int(d): n for d, n in rows if d is not None}
    return [{"label": names[d], "value": counts.get(d, 0)} for d in range(7)]


def _acquisition():
    rows = _rows(
        "SELECT date(timestamp) d, count(*) FROM books"
        " WHERE timestamp IS NOT NULL GROUP BY d ORDER BY d"
    )
    return [{"label": str(d), "value": n} for d, n in rows]


def _custom_column_breakdown(label):
    """[(value, count)] for an enumeration/text custom column, or []."""
    got = _rows(
        "SELECT id, datatype, normalized FROM custom_columns WHERE label = :l",
        l=label,
    )
    if not got:
        return []
    cid, normalized = got[0][0], got[0][2]
    try:
        if normalized:
            rows = _rows(
                "SELECT v.value, count(DISTINCT l.book) c"
                " FROM books_custom_column_%d_link l"
                " JOIN custom_column_%d v ON v.id = l.value"
                " GROUP BY v.value ORDER BY c DESC" % (cid, cid)
            )
        else:
            rows = _rows(
                "SELECT value, count(*) c FROM custom_column_%d"
                " GROUP BY value ORDER BY c DESC" % cid
            )
    except Exception as ex:
        log.info("custom column %s unreadable: %s", label, ex)
        return []
    return [{"label": str(v), "value": n} for v, n in rows if v is not None]


def _pace_by_year():
    """Books added per year, from cquarry's analytics module (Phase 7 swap:
    the derivation is database-shaped, so it lives upstream)."""
    from cquarry.analytics import addition_timeline

    from .library_cache import quarry

    try:
        timeline = addition_timeline(quarry(), granularity="year")
    except Exception as ex:
        log.info("acquisition pace unavailable: %s", ex)
        return []
    return [{"label": str(year), "value": n} for year, n in sorted(timeline.items())]


def _ratings():
    rated = _rows("SELECT count(DISTINCT book) FROM books_ratings_link")[0][0]
    return rated


def _rebuild():
    totals = _totals()
    books = totals["books"] or 1
    hours = _hour_histogram()
    peak = (
        max(hours, key=lambda h: h["value"]) if hours else {"label": "--", "value": 0}
    )
    acq = _acquisition()
    rated = _ratings()
    status = _custom_column_breakdown("reading_status")
    source = _custom_column_breakdown("source")

    data = {
        "totals": totals,
        "charts": {
            "decade": _by_decade(),
            "pace": _pace_by_year(),
            "formats": _formats(),
            "genres": _genre_spine(),
            "authors": _top("authors", "books_authors_link", "author"),
            "series": _top("series", "books_series_link", "series"),
            "publishers": _top("publishers", "books_publishers_link", "publisher"),
            "hours": hours,
            "weekdays": _weekday_histogram(),
        },
        "peak_hour": peak,
        "acquisition": {
            "days": len(acq),
            "first": acq[0]["label"] if acq else None,
            "last": acq[-1]["label"] if acq else None,
            "busiest": max(acq, key=lambda d: d["value"]) if acq else None,
        },
        # Degenerate axes: a chart of these would be one slice (spec 12.1)
        "readouts": {
            "rated": {"n": rated, "pct": round(rated * 100.0 / books, 1)},
            "status": status[:4],
            "source": source[:4],
        },
    }
    log.info("Statistics rebuilt: %d books", totals["books"])
    return data


_cache = LibraryCache(_rebuild)


def collect():
    """Everything the statistics surfaces need, cached on metadata.db's mtime."""
    return _cache.get()


# --- surfaces ---------------------------------------------------------------
# The metric functions above stay pure (spec 12.3): they return plain data and
# know nothing about HTML. Everything below is only routing and injection.


@statistics.route("/statistics")
@login_required_if_no_ano
def show_statistics():
    try:
        data = collect()
    except Exception as ex:
        # The page exists; the library behind it does not answer. 503 says
        # that, where an unguarded getmtime here used to raise a 500.
        log.error("Statistics unavailable: %s", ex)
        abort(503)
    return render_title_template(
        "statistics.html",
        stats=data,
        title=_("Statistics"),
        page="statistics",
    )


@statistics.app_context_processor
def inject_masthead():
    """The compact readout strip the front page carries."""
    try:
        data = collect()
    except Exception as ex:
        log.error("Statistics unavailable: %s", ex)
        return {"lib_stats": None}
    return {"lib_stats": data}
