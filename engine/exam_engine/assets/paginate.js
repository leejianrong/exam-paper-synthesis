/* The paper's paginator (P6b, EXA-138): lays a printed paper out page by page.
 *
 * Runs on a paper the renderer flagged with data-paginate on <main>. It measures the laid-out
 * paper once, works out where Chromium will start each page (questions never split, a heading
 * stays with the next block, a multi-part question may break between its parts), then wraps
 * each page's blocks in a fixed-height box and gives every question page its furniture: a
 * footer (tag, page number, "(Go on to the next page)" except on the last page), the marking
 * strip down the right when the page holds marked questions, and the tally box with that page's
 * marks (data-tally). When a page ends because the next question did not fit, the last working
 * space on it is stretched down to the footer. Printing the wrapped paper therefore gives
 * exactly the pages computed here (see docs/planning/editor/P6-SPIKE.md). Sets
 * <html data-paginated="true"> when done, also on papers it leaves alone, so the PDF step can
 * always wait for it.
 */
(function () {
  var MM = 96 / 25.4;
  var PAGE_H = (297 - 2 * 18) * MM; // content height of an A4 page under @page margin 18mm 16mm
  var FOOT_H = 16 * MM; // room kept clear at the foot of every page for the footer and tally
  var SLACK = 2; // px: rounding must never spill a blank page
  var MIN_SPACE_MM = 10; // working space is never clamped below this

  function done(warnings) {
    var root = document.documentElement;
    if (warnings && warnings.length) root.setAttribute("data-pagination-warnings", String(warnings.length));
    root.setAttribute("data-paginated", "true");
  }

  function images() {
    return Promise.all(
      Array.prototype.map.call(document.images, function (img) {
        return img.decode ? img.decode().catch(function () {}) : Promise.resolve();
      })
    );
  }

  function measure(kids, startsPage) {
    return kids.map(function (el) {
      var r = el.getBoundingClientRect();
      var cs = getComputedStyle(el);
      return {
        el: el,
        top: r.top + scrollY,
        bottom: r.bottom + scrollY,
        keepNext: cs.breakAfter === "avoid" || cs.breakAfter === "avoid-page",
        keepPrev: cs.breakBefore === "avoid" || cs.breakBefore === "avoid-page", // the end marker
        forced: cs.breakAfter === "page",
        // a blank page (P7) or a structured question (EXA-138) starts a page of its own
        forcedBefore: cs.breakBefore === "page" || startsPage.has(el),
      };
    });
  }

  // The last index of the run that must share a page with items[i].
  function runEnd(items, i) {
    var j = i;
    while (
      j < items.length - 1 &&
      (items[j].keepNext || items[j + 1].keepPrev) &&
      !items[j + 1].forcedBefore
    )
      j++;
    return j;
  }

  // A question taller than a page would be clipped. Shrink its blank working space (never below
  // MIN_SPACE_MM) by the overflow and report it; whatever text remains is left to overflow.
  // A heading is kept with the block after it, so the unit that must fit is the whole run.
  function clamp(items, sheetTop, avail, warnings) {
    var changed = false;
    var i = 0;
    while (i < items.length) {
      var j = runEnd(items, i);
      var from = i === 0 ? sheetTop : items[i].top; // page 1 also holds the paper's header
      var over = items[j].bottom - from - avail;
      if (over > 0) {
        var cut = 0;
        for (var k = j; k >= i; k--) {
          var spaces = items[k].el.querySelectorAll(".answer-space");
          for (var s = 0; s < spaces.length; s++) {
            var h = spaces[s].getBoundingClientRect().height;
            var take = Math.min(Math.max(0, h - MIN_SPACE_MM * MM), over - cut);
            if (take > 0) {
              spaces[s].style.height = h - take + "px";
              spaces[s].style.minHeight = "0";
              cut += take;
            }
          }
        }
        if (cut > 0) changed = true;
        warnings.push({ index: i, cutMm: Math.round(cut / MM), overflowMm: Math.round((over - cut) / MM) });
      }
      i = j + 1;
    }
    return changed;
  }

  // Greedy fragmentation: the page index of every block.
  function paginate(items, base, avail) {
    var pageOf = [];
    var page = 0;
    var placed = 0; // groups already on the current page: never leave a page empty
    var i = 0;
    while (i < items.length) {
      var j = runEnd(items, i);
      if (items[i].forcedBefore && placed > 0) {
        page++;
        placed = 0;
        base = items[i].top;
      }
      if (items[j].bottom - base > avail && placed > 0) {
        page++;
        placed = 0;
        base = items[i].top;
      }
      for (var k = i; k <= j; k++) pageOf[k] = page;
      placed++;
      if (items[j].forced) {
        page++;
        placed = 0;
        if (j + 1 < items.length) base = items[j + 1].top;
      }
      i = j + 1;
    }
    return pageOf;
  }

  function marksOf(el) {
    var n = 0;
    var tagged = el.hasAttribute("data-marks") ? [el] : [];
    tagged = tagged.concat(Array.prototype.slice.call(el.querySelectorAll("[data-marks]")));
    tagged.forEach(function (t) {
      n += parseInt(t.getAttribute("data-marks"), 10) || 0;
    });
    return n;
  }

  function tallyBox(template, total) {
    var box = template.content.firstElementChild.cloneNode(true);
    box.setAttribute("aria-label", "Marks awarded out of " + total);
    box.querySelector(".tally-total").textContent = String(total);
    return box;
  }

  function marginStrip() {
    var strip = document.createElement("div");
    strip.className = "margin-strip";
    strip.setAttribute("aria-hidden", "true");
    strip.innerHTML = "<span>Do not write in this space</span>";
    return strip;
  }

  // Stretch the working space of the last question on a page that ends early down to the
  // footer, so the page does not end on a white gap under a small box. Its Ans: lines move down
  // with it; the parts of a multi-part question share the extra room equally.
  function fill(pg) {
    var flow = Array.prototype.filter.call(pg.children, function (c) {
      return !c.classList.contains("page-foot") && !c.classList.contains("margin-strip");
    });
    var last = flow[flow.length - 1];
    var spaces = last ? last.querySelectorAll(".answer-space") : [];
    if (!spaces.length) return;
    var bottom = last.getBoundingClientRect().bottom + parseFloat(getComputedStyle(last).marginBottom);
    var free = pg.getBoundingClientRect().top + pg.clientHeight - FOOT_H - bottom - SLACK;
    if (free <= 1) return;
    var each = free / spaces.length;
    Array.prototype.forEach.call(spaces, function (space) {
      space.style.height = space.getBoundingClientRect().height + each + "px";
      space.style.minHeight = "0";
      space.setAttribute("data-filled", "");
    });
  }

  function build() {
    var main = document.querySelector("main[data-paginate]");
    var body = main && main.querySelector(".doc-body");
    var footTemplate = document.getElementById("page-foot-template");
    var tallyTemplate = document.getElementById("tally-template");
    if (!body || !footTemplate || !body.children.length) return done();

    // A multi-part question is counted part by part, so it may break between its parts: its
    // parts stand in for it, and `owner` remembers which question each one belongs to.
    var owner = new Map();
    var startsPage = new Set(); // the first part of a question that starts a page of its own
    var kids = [];
    Array.prototype.forEach.call(body.children, function (el) {
      var units = el.querySelectorAll(":scope > .part-unit");
      if (!units.length) return kids.push(el);
      if (getComputedStyle(el).breakBefore === "page") startsPage.add(units[0]);
      Array.prototype.forEach.call(units, function (u) {
        owner.set(u, el);
        kids.push(u);
      });
    });
    var sheetTop = main.getBoundingClientRect().top + scrollY;
    var avail = PAGE_H - FOOT_H;
    var warnings = [];

    var items = measure(kids, startsPage);
    // The header sits above the first block on page 1, so that page has less room.
    var head = items[0].top - sheetTop;
    if (clamp(items, sheetTop, avail, warnings)) items = measure(kids, startsPage);

    var pageOf = paginate(items, sheetTop, avail);
    var pages = [];
    var placed = new Set();
    items.forEach(function (it, i) {
      (pages[pageOf[i]] = pages[pageOf[i]] || { items: [], marks: 0 });
      pages[pageOf[i]].items.push(it.el);
      pages[pageOf[i]].marks += marksOf(it.el);
    });

    var boxes = [];
    pages.forEach(function (p, n) {
      if (!p) return;
      var pg = document.createElement("div");
      pg.className = "pg";
      pg.style.height = PAGE_H - SLACK - (n === 0 ? head : 0) + "px";
      if (n === pages.length - 1) pg.style.breakAfter = "auto";
      body.appendChild(pg);
      var frag = null;
      p.items.forEach(function (el) {
        var q = owner.get(el);
        if (!q) {
          frag = null;
          return pg.appendChild(el);
        }
        if (!frag || frag.q !== q) {
          // the first page of a question keeps the question itself, later ones a numberless copy
          var node = placed.has(q) ? q.cloneNode(false) : q;
          if (node !== q) node.classList.add("cont");
          placed.add(q);
          pg.appendChild(node);
          frag = { q: q, node: node };
        }
        frag.node.appendChild(el);
      });
      boxes.push({ pg: pg, marks: p.marks });
    });

    // A cover or blank page carries no footer; the page number still counts it (the cover is
    // page 1, as on real booklets). The last question page ends the paper: no "Go on" there.
    var questionPage = function (b) {
      return !b.pg.querySelector(".cover-page, .blank-page");
    };
    var last = boxes.length - 1;
    boxes.forEach(function (b, n) {
      if (b.pg.querySelector(".end-marker")) last = n;
    });
    boxes.forEach(function (b, n) {
      var pg = b.pg;
      if (!questionPage(b)) return;
      if (pg.querySelector(".question.marked")) {
        pg.classList.add("marked");
        pg.appendChild(marginStrip());
      }
      var foot = footTemplate.content.firstElementChild.cloneNode(true);
      foot.querySelector(".foot-num").textContent = String(n + 1);
      if (n >= last) foot.querySelector(".foot-go").remove();
      if (b.marks > 0 && tallyTemplate) foot.querySelector(".foot-end").appendChild(tallyBox(tallyTemplate, b.marks));
      pg.appendChild(foot);
      // Whatever could not be made to fit is printed in full (Chromium splits it) rather than cut.
      if (pg.scrollHeight > pg.clientHeight + 1) {
        pg.style.height = "auto";
        pg.style.overflow = "visible";
      } else if (n < last) {
        fill(pg);
      }
    });
    done(warnings);
  }

  function run() {
    try {
      build();
    } catch (e) {
      done([{ error: String(e) }]); // never leave the export waiting for the flag
    }
  }

  function start() {
    var ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    ready.then(images).then(function () {
      // KaTeX sets its flag synchronously at DOMContentLoaded, which is before this runs.
      requestAnimationFrame(run);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
