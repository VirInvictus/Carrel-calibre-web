/* Carrel command palette.
   Ctrl-K (or "/") opens a terminal-styled fuzzy jumper over every wing,
   author, series, category, and page. Self-contained: injects its own styles
   from the theme's token variables and reads window.PALETTE, emitted by
   /palette-data.js. No data file, no palette: the app works without it.

   Ported from the palette in Brandon's Athenaeum static site; the scoring
   function and keyboard model are carried over intact, the styling is
   repointed at Carrel's Dragon tokens. */
(function () {
  "use strict";
  var DATA = window.PALETTE || [];
  if (!DATA.length || !document.body) return;

  var css =
    ".cp-veil{position:fixed;inset:0;z-index:2000;background:rgba(13,12,12,.66);backdrop-filter:blur(3px)}" +
    ".cp{position:absolute;left:50%;top:15vh;transform:translateX(-50%);width:min(600px,92vw);" +
    "font-family:var(--mono,ui-monospace,monospace);background:var(--kngw-black2);" +
    "border:1px solid var(--kngw-black5);border-radius:var(--radius,3px);" +
    "box-shadow:0 18px 50px rgba(0,0,0,.6)}" +
    ".cp-head{display:flex;align-items:center;gap:10px;padding:13px 15px;" +
    "border-bottom:1px solid var(--kngw-black4)}" +
    ".cp-gt{color:var(--kngw-orange);font-weight:600}" +
    ".cp-in{flex:1;background:transparent;border:0;outline:0;color:var(--kngw-fuji-white);" +
    "font-family:inherit;font-size:14px;letter-spacing:.02em}" +
    ".cp-in::placeholder{color:var(--kngw-black6)}" +
    ".cp-list{max-height:46vh;overflow-y:auto;padding:6px 0;" +
    "scrollbar-width:thin;scrollbar-color:var(--kngw-black5) transparent}" +
    ".cp-list::-webkit-scrollbar{width:8px}" +
    ".cp-list::-webkit-scrollbar-track{background:transparent}" +
    ".cp-list::-webkit-scrollbar-thumb{background:var(--kngw-black5);border-radius:3px}" +
    ".cp-row{display:flex;align-items:baseline;gap:12px;padding:7px 15px;cursor:pointer;" +
    "border-left:2px solid transparent;font-size:13px;color:var(--kngw-white)}" +
    ".cp-row .g{margin-left:auto;font-size:10px;color:var(--kngw-black6);" +
    "text-transform:uppercase;letter-spacing:.09em;white-space:nowrap}" +
    ".cp-row.sel{border-left-color:var(--kngw-orange);background:var(--kngw-black4);" +
    "color:var(--kngw-fuji-white)}" +
    ".cp-row.sel .g{color:var(--kngw-orange)}" +
    ".cp-none{padding:14px 15px;font-size:12px;color:var(--kngw-black6)}" +
    ".cp-foot{display:flex;justify-content:space-between;padding:8px 15px;" +
    "border-top:1px solid var(--kngw-black4);font-size:10px;letter-spacing:.08em;" +
    "text-transform:uppercase;color:var(--kngw-black6)}";
  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  var veil = document.createElement("div");
  veil.className = "cp-veil";
  veil.hidden = true;
  veil.innerHTML =
    '<div class="cp" role="dialog" aria-modal="true" aria-label="Command palette">' +
    '<div class="cp-head"><span class="cp-gt">&gt;</span>' +
    '<input class="cp-in" type="text" placeholder="jump anywhere — a authors · s series · c categories · w wings" ' +
    'spellcheck="false" autocomplete="off" aria-label="Search the library"></div>' +
    '<div class="cp-list" role="listbox"></div>' +
    '<div class="cp-foot"><span>&#8593;&#8595; navigate &middot; &#8629; open &middot; esc close</span>' +
    '<span class="cp-n"></span></div></div>';
  document.body.appendChild(veil);

  var input = veil.querySelector(".cp-in");
  var list = veil.querySelector(".cp-list");
  var nEl = veil.querySelector(".cp-n");
  var results = [];
  var sel = 0;

  function score(q, entry) {
    var t = entry.t.toLowerCase();
    var g = (entry.g || "").toLowerCase();
    if (!q) return 1;
    var idx = t.indexOf(q);
    if (idx >= 0) return 200 - idx - t.length / 50; // substring: earlier + shorter wins
    if (g.indexOf(q) >= 0) return 40; // group text (e.g. "wing", "author")
    var qi = 0, gaps = 0, last = -2; // subsequence with gap penalty
    for (var i = 0; i < t.length && qi < q.length; i++) {
      if (t[i] === q[qi]) {
        if (i !== last + 1) gaps++;
        last = i;
        qi++;
      }
    }
    return qi === q.length ? 100 - gaps * 8 - t.length / 50 : -1;
  }

  // A prefix letter plus a space scopes the haystack to one shelf:
  // "a tolkien" searches the authors, "s dune" the series. The search
  // fallback below always sees the full query, prefix included.
  var PREFIXES = { w: "wing", a: "author", s: "series", c: "category", p: "page" };

  function scope(q) {
    var m = /^([wascp])\s+(.*)$/.exec(q);
    if (!m || !PREFIXES[m[1]]) return { data: DATA, q: q };
    var group = PREFIXES[m[1]];
    return {
      data: DATA.filter(function (e) { return e.g === group; }),
      q: m[2],
    };
  }

  function update() {
    var sc = scope(input.value.trim().toLowerCase());
    var q = sc.q;
    results = sc.data.map(function (e) { return { e: e, s: score(q, e) }; })
      .filter(function (r) { return r.s > 0; })
      .sort(function (a, b) { return b.s - a.s; })
      .slice(0, 12)
      .map(function (r) { return r.e; });
    sel = 0;
    list.innerHTML = "";
    var hits = results.length;
    // Fall through to the search grammar: the palette jumps to things that
    // exist, but a query is often the actual intent, and the parity engine is
    // the most capable thing in the app. Always last, so it never displaces a
    // real destination.
    if (q) {
      results.push({
        t: input.value.trim(),
        g: "search",
        h: "/search?query=" + encodeURIComponent(input.value.trim()),
      });
    }
    // No "results is empty" branch: an empty query scores every entry at 1 and
    // a non-empty one always appends the search fallback, so by this point
    // results never is. The reachable no-match message is the one below.
    if (q && !hits) {
      // No destination matched, so say so above the search row rather than
      // leaving it looking like a match.
      var none = document.createElement("div");
      none.className = "cp-none";
      none.textContent = "nothing shelved under that name \u2014 search instead?";
      list.appendChild(none);
    }
    results.forEach(function (e, i) {
      var row = document.createElement("div");
      row.className = "cp-row" + (i === sel ? " sel" : "");
      row.setAttribute("role", "option");
      var name = document.createElement("span");
      name.textContent = e.t;
      var grp = document.createElement("span");
      grp.className = "g";
      grp.textContent = e.g || "";
      row.appendChild(name);
      row.appendChild(grp);
      row.addEventListener("click", function () { go(e); });
      row.addEventListener("pointermove", function () { setSel(i); });
      list.appendChild(row);
    });
    nEl.textContent = hits + " of " + sc.data.length;
  }

  function setSel(i) {
    sel = Math.max(0, Math.min(results.length - 1, i));
    var rows = list.querySelectorAll(".cp-row");
    rows.forEach(function (r, j) { r.classList.toggle("sel", j === sel); });
    if (rows[sel]) rows[sel].scrollIntoView({ block: "nearest" });
  }

  function go(e) { location.href = e.h; }
  function open() { veil.hidden = false; input.value = ""; update(); input.focus(); }
  function close() { veil.hidden = true; }

  veil.addEventListener("pointerdown", function (ev) { if (ev.target === veil) close(); });
  input.addEventListener("input", update);
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "ArrowDown") { setSel(sel + 1); ev.preventDefault(); }
    else if (ev.key === "ArrowUp") { setSel(sel - 1); ev.preventDefault(); }
    else if (ev.key === "Enter" && results[sel]) go(results[sel]);
  });
  document.addEventListener("keydown", function (ev) {
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
      ev.preventDefault();
      veil.hidden ? open() : close();
    } else if (ev.key === "Escape" && !veil.hidden) close();
    else if (
      ev.key === "/" &&
      !ev.ctrlKey &&
      !ev.altKey &&
      !ev.metaKey &&
      veil.hidden
    ) {
      var t = ev.target;
      if (!(t instanceof HTMLElement) || !t.closest("input,textarea,select,[contenteditable]")) {
        ev.preventDefault();
        open();
      }
    }
  });

  window.__palette = { open: open, close: close, count: DATA.length };
})();
