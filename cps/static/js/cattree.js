/* Carrel category tree: remember what is open across page changes.

   The tree is server-rendered <details>, so without this every navigation
   collapses it back and the browser is unusable for anything more than one
   click deep. The server already opens the ancestors of the active category;
   this restores whatever else the reader had expanded.

   Degrades cleanly: no localStorage, no tree, or a thrown quota error just
   leaves the plain <details> behaviour. */
(function () {
  "use strict";
  var KEY = "carrel.cat.open";
  var nodes = document.querySelectorAll("details[data-cat]");
  if (!nodes.length) return;

  function load() {
    try {
      return new Set(JSON.parse(localStorage.getItem(KEY) || "[]"));
    } catch (e) {
      return new Set();
    }
  }

  function save(set) {
    try {
      localStorage.setItem(KEY, JSON.stringify(Array.from(set)));
    } catch (e) {
      /* private mode or quota: persistence is a nicety, not a requirement */
    }
  }

  var open = load();

  nodes.forEach(function (d) {
    var key = d.getAttribute("data-cat");
    // The server opens the active path; keep it open and record it, so
    // walking down into a category does not silently forget the branch.
    if (d.open) {
      open.add(key);
    } else if (open.has(key)) {
      d.open = true;
    }
    d.addEventListener("toggle", function () {
      if (d.open) {
        open.add(key);
      } else {
        open.delete(key);
      }
      save(open);
    });
  });

  save(open);
})();
