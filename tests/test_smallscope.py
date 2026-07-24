# -*- coding: utf-8 -*-

# Tests for the smallscope adaptations (calibre-web-kanagawa spec 5-8):
# enum read column (read-only), mode=ro library guarantee, trimmed routes,
# and Wings. Runs the real Flask app against a fixture metadata.db in a
# throwaway CALIBRE_DBPATH; never touches a real library.
#
# Run from the repo root:  ~/calibre-web-env/bin/python -m unittest discover -s tests

import hashlib
import os
import sqlite3
import sys
import tempfile
import unittest

# cps's cli parser reads sys.argv at create_app time; hide unittest's args.
sys.argv = ["cps.py"]

# CALIBRE_DBPATH must point at the sandbox BEFORE cps is imported.
_TMP = tempfile.mkdtemp(prefix="cw_smallscope_test_")
os.environ["CALIBRE_DBPATH"] = _TMP

LIB = os.path.join(_TMP, "library")
os.makedirs(LIB)
DBPATH = os.path.join(LIB, "metadata.db")

from tests.fixture import build_fixture  # noqa: E402

build_fixture(DBPATH)

from cps import calibre_db, config, create_app, ub  # noqa: E402

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False

# Mirror main()'s registration (minus kobo/oauth/gdrive specials and the
# web server). Keep in sync with cps/main.py when rebasing.
from cps.about import about  # noqa: E402
from cps.admin import admi  # noqa: E402
from cps.basic import basic  # noqa: E402
from cps.editbooks import editbook  # noqa: E402
from cps.jinjia import jinjia  # noqa: E402
from cps.opds import opds  # noqa: E402
from cps.remotelogin import remotelogin  # noqa: E402
from cps.search import search  # noqa: E402
from cps.search_metadata import meta  # noqa: E402
from cps.shelf import shelf  # noqa: E402
from cps.single_user import install as install_single_user  # noqa: E402
from cps.smallscope import read_column_is_enum, trim  # noqa: E402
from cps.tasks_status import tasks  # noqa: E402
from cps.web import web  # noqa: E402
from cps.wings import wings  # noqa: E402

trim(tasks, shelf, editbook, remotelogin)
install_single_user(app)
for blueprint in (
    search,
    tasks,
    web,
    basic,
    opds,
    jinjia,
    about,
    wings,
    shelf,
    admi,
    remotelogin,
    meta,
    editbook,
):
    app.register_blueprint(blueprint)

# Point the instance at the fixture library, link the enum column, enable
# the caliBlur theme and the Read/Unread sidebar sections for admin.
config.config_calibre_dir = LIB
config.config_read_column = 2
config.config_theme = 1
config.save()
# Bind the config to the library; sessions connect lazily per request.
calibre_db.update_config(config, LIB, ub.app_DB_path)
# Force one connect so cc_classes is populated before the first test request
# (get_book_read_archived consults cc_classes before touching the session).
with app.test_request_context("/"):
    assert calibre_db.session is not None, "fixture library failed to connect"
with app.app_context():
    user = ub.session.query(ub.User).filter(ub.User.name == "admin").one()
    user.sidebar_view |= 256  # SIDEBAR_READ_AND_UNREAD
    user.sidebar_view &= ~1  # no DETAIL_RANDOM strip: keeps grid assertions exact
    ub.session.commit()


def _md5(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def tearDownModule():
    # create_app starts non-daemon threads (updater, APScheduler); stop them
    # or the interpreter hangs in threading shutdown after the run.
    try:
        from cps.services.background_scheduler import BackgroundScheduler

        if BackgroundScheduler._instance is not None:
            BackgroundScheduler._instance.scheduler.shutdown(wait=False)
    except Exception:
        pass
    try:
        from cps import updater_thread

        updater_thread.stop()
    except Exception:
        pass
    import shutil

    shutil.rmtree(_TMP, ignore_errors=True)


class SmallscopeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # No login: spec 11 authenticates the owner on every request. If the
        # shim regressed, every assertion below would fail on a redirect to a
        # login page that no longer exists.
        cls.client = app.test_client()

    # --- enum read column ------------------------------------------------

    def test_read_column_is_enum(self):
        self.assertTrue(read_column_is_enum(2))
        self.assertFalse(read_column_is_enum(5))
        self.assertFalse(read_column_is_enum(99))

    def test_detail_badges_show_enum_state(self):
        expected = {1: "read", 2: "reading", 3: "toread", 4: "dnf"}
        for book_id, state in expected.items():
            page = self.client.get("/book/%d" % book_id).get_data(as_text=True)
            self.assertIn(
                "kngw-status-%s" % state,
                page,
                "book %d should show %s" % (book_id, state),
            )
            self.assertNotIn("have_read_form", page)

    def test_read_section_is_exactly_the_read_books(self):
        page = self.client.get("/read/stored").get_data(as_text=True)
        self.assertIn("Ancillary Justice", page)
        for title in ("Ancillary Sword", "Dune", "Gardens of the Moon"):
            self.assertNotIn(title, page)

    def test_unread_section_is_everything_else(self):
        page = self.client.get("/unread/stored").get_data(as_text=True)
        self.assertNotIn("Ancillary Justice", page)
        for title in ("Ancillary Sword", "Dune", "Gardens of the Moon"):
            self.assertIn(title, page)

    def test_toggle_refused_and_library_untouched(self):
        before = _md5(DBPATH)
        rv = self.client.post("/ajax/toggleread/1")
        self.assertEqual(rv.status_code, 400)
        self.assertIn("read-only", rv.get_data(as_text=True))
        self.assertEqual(before, _md5(DBPATH))

    def test_bool_column_cannot_write_readonly_library(self):
        # Upstream bool toggle path stays selectable but the mode=ro attach
        # makes the write fail; the library file must be untouched.
        before = _md5(DBPATH)
        config.config_read_column = 5
        try:
            page = self.client.get("/book/1").get_data(as_text=True)
            self.assertIn("have_read_form", page)  # bool path keeps the checkbox
            self.assertNotIn("kngw-status", page)
            rv = self.client.post("/ajax/toggleread/1")
            self.assertEqual(rv.status_code, 400)
        finally:
            config.config_read_column = 2
        self.assertEqual(before, _md5(DBPATH))

    def test_library_attached_readonly(self):
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError

        with app.app_context():
            with self.assertRaises(OperationalError) as ctx:
                calibre_db.session.execute(
                    text("UPDATE calibre.books SET title='x' WHERE id=1")
                )
                calibre_db.session.commit()
            calibre_db.session.rollback()
            self.assertIn("readonly", str(ctx.exception).lower())

    # --- trimmed surface --------------------------------------------------

    def test_trimmed_routes_404(self):
        for url in ("/tasks", "/shelf/1", "/admin/book/1"):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    # --- single user (spec 11) ---------------------------------------------

    def test_library_renders_without_any_credential(self):
        # A client that has never seen a cookie, let alone a login form.
        fresh = app.test_client()
        rv = fresh.get("/")
        self.assertEqual(rv.status_code, 200)
        self.assertIn("/book/", rv.get_data(as_text=True))

    def test_credential_paths_are_sealed(self):
        for url in ("/login", "/logout", "/register", "/login/",
                    "/admin/user/new", "/admin/usertable"):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_login_required_pages_pass_through(self):
        # /me carries @login_required upstream. 200 here proves the decorator
        # is satisfied rather than removed.
        self.assertEqual(self.client.get("/me").status_code, 200)

    def test_request_runs_as_the_owning_admin(self):
        from cps.cw_login import current_user

        with app.test_request_context("/"):
            app.preprocess_request()
            self.assertTrue(current_user.is_authenticated)
            self.assertEqual(current_user.name, "admin")

    # --- wings -------------------------------------------------------------

    def test_wings_sidebar_names_and_counts(self):
        page = self.client.get("/").get_data(as_text=True)
        for fragment in ("wings/SciFi", "wings/Hugo", "wings/NotHugo", "wings/Empty"):
            self.assertIn(fragment, page)
        # SciFi: hierarchical tags:"Fic.SciFi" matches books 1, 2, 3
        self.assertIn('SciFi <span class="badge badge-sm">3', page)
        self.assertIn('Hugo <span class="badge badge-sm">1', page)
        # NotHugo: vl: cross-reference resolves to books 2, 3, 4
        self.assertIn('NotHugo <span class="badge badge-sm">3', page)

    def test_wing_page_filters_exactly(self):
        page = self.client.get("/wings/Hugo").get_data(as_text=True)
        self.assertIn("Ancillary Justice", page)
        self.assertNotIn("Dune", page)
        self.assertEqual(self.client.get("/wings/Empty").status_code, 200)
        self.assertEqual(self.client.get("/wings/Nope").status_code, 404)

    def test_wings_cache_invalidates_on_mtime(self):
        sqlite3_path = DBPATH
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("wings/Fantasy", page)
        con = sqlite3.connect(sqlite3_path)
        import json

        row = con.execute(
            "SELECT val FROM preferences WHERE key='virtual_libraries'"
        ).fetchone()
        wings_map = json.loads(row[0])
        wings_map["Fantasy"] = 'tags:"Fic.Fantasy"'
        con.execute(
            "UPDATE preferences SET val=? WHERE key='virtual_libraries'",
            (json.dumps(wings_map),),
        )
        con.commit()
        con.close()
        os.utime(sqlite3_path)  # ensure the mtime moves even on coarse clocks
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("wings/Fantasy", page)
        self.assertIn('Fantasy <span class="badge badge-sm">1', page)


if __name__ == "__main__":
    unittest.main()
