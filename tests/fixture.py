# -*- coding: utf-8 -*-

# Calibre metadata.db fixture for the smallscope tests. The table schema is
# dumped from a real Calibre library (tests/calibre_schema.sql; tables only,
# no triggers, custom_column tables excluded) so the fork's ORM always finds
# the columns it expects. On top of that: an enumeration reading-status
# column (cc2, like the real library), a bool column (cc5) for the
# upstream-path regression test, and virtual libraries including a vl:
# cross-reference.

import os
import sqlite3

_SCHEMA_SQL = os.path.join(os.path.dirname(__file__), "calibre_schema.sql")

CUSTOM_COLUMNS_SCHEMA = """
CREATE TABLE custom_columns (id INTEGER PRIMARY KEY, label TEXT, name TEXT,
    datatype TEXT, mark_for_delete BOOL DEFAULT 0, editable BOOL DEFAULT 1,
    display TEXT DEFAULT '{}', is_multiple BOOL DEFAULT 0, normalized BOOL);
-- cc2: normalized enumeration (value table + link table), like the real library
CREATE TABLE custom_column_2 (id INTEGER PRIMARY KEY, value TEXT, link TEXT DEFAULT '');
CREATE TABLE books_custom_column_2_link (book INT, value INT);
-- cc5: bool column (direct book/value rows)
CREATE TABLE custom_column_5 (id INTEGER PRIMARY KEY, book INT, value BOOL);
"""

BOOKS = [
    # (id, title, enum status or None)
    (1, "Ancillary Justice", "Read"),
    (2, "Ancillary Sword", "Reading"),
    (3, "Dune", None),  # no row -> displays as To Read
    (4, "Gardens of the Moon", "DNF"),
]


def build_fixture(path, extra_wings=None):
    con = sqlite3.connect(path)
    with open(_SCHEMA_SQL, encoding="utf-8") as fh:
        con.executescript(fh.read())
    con.executescript(CUSTOM_COLUMNS_SCHEMA)
    cur = con.cursor()
    cur.executemany(
        "INSERT INTO authors (id,name,sort) VALUES (?,?,?)",
        [
            (1, "Ann Leckie", "Leckie, Ann"),
            (2, "Frank Herbert", "Herbert, Frank"),
            (3, "Steven Erikson", "Erikson, Steven"),
        ],
    )
    for book_id, title, _status in BOOKS:
        cur.execute(
            "INSERT INTO books (id,title,sort,author_sort,timestamp,pubdate,"
            "has_cover,last_modified,series_index,path,uuid) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                book_id,
                title,
                title,
                "x",
                "2024-01-0%d" % book_id,
                "2013-10-01",
                0,
                "2024-01-0%d" % book_id,
                1.0,
                "a/b (%d)" % book_id,
                "u%d" % book_id,
            ),
        )
    cur.executemany(
        "INSERT INTO books_authors_link (book,author) VALUES (?,?)",
        [(1, 1), (2, 1), (3, 2), (4, 3)],
    )
    cur.executemany(
        "INSERT INTO tags (id,name) VALUES (?,?)",
        [
            (1, "Fic.SciFi"),
            (2, "Fic.SciFi.Space"),
            (3, "Award.Hugo"),
            (4, "Fic.Fantasy.Epic"),
        ],
    )
    cur.executemany(
        "INSERT INTO books_tags_link (book,tag) VALUES (?,?)",
        [(1, 2), (1, 3), (2, 2), (3, 1), (4, 4)],
    )
    # Series so the palette index and series browse have something real to
    # exercise; without one, whole code paths look covered but never run.
    # Two of them, because the /<data>/<sort_param>/<id> shape bug can only be
    # detected against an entity whose id is not 1: with a single series every
    # link "works" by landing on the fallback.
    cur.executemany(
        "INSERT INTO series (id,name,sort) VALUES (?,?,?)",
        [
            (1, "The Broken Earth", "Broken Earth, The"),
            (2, "Dune Chronicles", "Dune Chronicles"),
        ],
    )
    cur.executemany(
        "INSERT INTO books_series_link (book,series) VALUES (?,?)",
        [(1, 1), (2, 1), (3, 2)],
    )
    cur.execute("INSERT INTO languages (id,lang_code) VALUES (1,'eng')")
    cur.executemany(
        "INSERT INTO books_languages_link (book,lang_code) VALUES (?,1)",
        [(1,), (2,), (3,), (4,)],
    )
    cur.executemany(
        "INSERT INTO data (book,format,name,uncompressed_size) VALUES (?,?,?,100)",
        [(1, "EPUB", "x"), (2, "EPUB", "x"), (3, "EPUB", "x"), (4, "EPUB", "x")],
    )
    cur.executemany(
        "INSERT INTO comments (book,text) VALUES (?,?)",
        [(b, "text") for b in (1, 2, 3, 4)],
    )
    cur.execute("INSERT INTO library_id (uuid) VALUES ('smallscope-test-uuid')")

    wings = {
        "SciFi": 'tags:"Fic.SciFi"',  # hierarchical: books 1, 2, 3
        "Hugo": "tags:Award.Hugo",  # book 1
        "NotHugo": 'not vl:"Hugo"',  # books 2, 3, 4 (vl: cross-ref)
        "Empty": 'tags:"Nothing.Here"',  # no books
        # Hidden in Calibre's own UI: get_vl_ui_state must keep it out
        # of the sidebar while it stays resolvable by direct route.
        "Secret": "tags:Award.Hugo",
    }
    wings.update(extra_wings or {})
    import json

    cur.execute(
        "INSERT INTO preferences (key,val) VALUES ('virtual_libraries', ?)",
        (json.dumps(wings),),
    )
    cur.execute(
        "INSERT INTO preferences (key,val) VALUES ('virt_libs_order', ?)",
        (json.dumps({"SciFi": 0, "Hugo": 1}),),
    )
    cur.execute(
        "INSERT INTO preferences (key,val) VALUES ('virt_libs_hidden', ?)",
        (json.dumps(["Secret"]),),
    )
    # Saved searches exercise cquarry's search:"Name" interpolation end to end:
    # one matching one book, one matching one, one matching nothing.
    cur.execute(
        "INSERT INTO preferences (key,val) VALUES ('saved_searches', ?)",
        (
            json.dumps(
                {
                    "Hugo Winners": "tags:Award.Hugo",
                    "Space": 'tags:"Fic.SciFi.Space"',
                    "Nothing": 'tags:"Nothing.Here"',
                }
            ),
        ),
    )

    # Reader state (cquarry extractors): highlights plus two devices whose
    # epoch_time decides the winner regardless of row order.
    cur.executemany(
        "INSERT INTO annotations (book, format, user_type, user, timestamp,"
        " annot_id, annot_type, annot_data) VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                1,
                "EPUB",
                "local",
                "reader",
                1767225600,
                "a1",
                "highlight",
                json.dumps({"text": "mind is not a vessel"}),
            ),
        ],
    )
    cur.executemany(
        "INSERT INTO last_read_positions (book, format, user, device,"
        " cfi, epoch, pos_frac) VALUES (?,?,?,?,?,?,?)",
        [
            (1, "EPUB", "reader", "kobo", "epubcfi(/6/4)", 100, 0.42),
            (1, "EPUB", "reader", "phone", "epubcfi(/6/9)", 200, 0.90),
        ],
    )
    cur.executemany(
        "INSERT INTO custom_columns (id,label,name,datatype,is_multiple,normalized) "
        "VALUES (?,?,?,?,0,?)",
        [
            (2, "reading_status", "Status", "enumeration", 1),
            (5, "readbool", "Read (bool)", "bool", 0),
        ],
    )
    values = sorted({status for _i, _t, status in BOOKS if status})
    for n, value in enumerate(values, start=1):
        cur.execute("INSERT INTO custom_column_2 (id,value) VALUES (?,?)", (n, value))
    for book_id, _title, status in BOOKS:
        if status:
            cur.execute(
                "INSERT INTO books_custom_column_2_link (book,value) "
                "SELECT ?, id FROM custom_column_2 WHERE value = ?",
                (book_id, status),
            )
    cur.execute("INSERT INTO custom_column_5 (book,value) VALUES (1,1)")
    con.commit()
    con.close()
