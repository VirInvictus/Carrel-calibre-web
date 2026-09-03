/* Carrel keyboard navigation.

   Moving through 7,000 books with a mouse is the wrong shape for a library
   you actually live in. j/k and the arrows walk the grid, Enter opens, and
   the terminal register the theme already speaks extends to the hands.

   Vanilla and self-contained. Does nothing if there is no grid, and never
   swallows a key while you are typing. */
(function () {
  "use strict";

  var books = Array.prototype.slice.call(
    document.querySelectorAll(".book .meta .title a, .book .cover > a")
  );
  // One entry per book: prefer the cover link, fall back to the title link.
  var seen = Object.create(null);
  var items = [];
  books.forEach(function (a) {
    var href = a.getAttribute("href");
    if (!href || seen[href]) return;
    seen[href] = true;
    items.push(a.closest(".book") || a);
  });
  if (!items.length) return;

  var idx = -1;

  function typing(el) {
    return (
      el instanceof HTMLElement &&
      (el.closest("input, textarea, select, [contenteditable]") !== null)
    );
  }

  function paletteOpen() {
    var veil = document.querySelector(".cp-veil");
    return veil && !veil.hidden;
  }

  function modalOpen() {
    // Bootstrap marks the body while a modal (the book-detail one, the
    // config dialogs) is up; j/k belong to whatever the modal holds.
    return (
      document.body.classList.contains("modal-open") ||
      !!document.querySelector(".modal.in, .modal.show, dialog[open]")
    );
  }

  function focus(n) {
    if (idx >= 0 && items[idx]) items[idx].classList.remove("kn-sel");
    idx = Math.max(0, Math.min(items.length - 1, n));
    var el = items[idx];
    el.classList.add("kn-sel");
    el.scrollIntoView({ block: "nearest" });
  }

  function open() {
    if (idx < 0) return;
    var a = items[idx].querySelector(".meta .title a, .cover > a");
    // The cover link opens a modal; the title link is a real navigation.
    var title = items[idx].querySelector(".meta .title a");
    var href = (title || a) && (title || a).getAttribute("href");
    if (href) location.href = href;
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (typing(ev.target) || paletteOpen() || modalOpen()) return;

    switch (ev.key) {
      case "j":
      case "ArrowDown":
        focus(idx + 1);
        ev.preventDefault();
        break;
      case "k":
      case "ArrowUp":
        focus(idx - 1);
        ev.preventDefault();
        break;
      case "g":
        focus(0);
        ev.preventDefault();
        break;
      case "G":
        focus(items.length - 1);
        ev.preventDefault();
        break;
      case "Enter":
        if (idx >= 0) {
          open();
          ev.preventDefault();
        }
        break;
      case "Escape":
        if (idx >= 0 && items[idx]) items[idx].classList.remove("kn-sel");
        idx = -1;
        break;
      default:
        break;
    }
  });
})();
