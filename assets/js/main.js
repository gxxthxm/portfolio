(function () {
  var doc = document.documentElement;
  var header = document.querySelector(".site-header");
  // "?shot" renders a still page for mockup screenshots: no intro, no motion.
  var shot = /[?&]shot\b/.test(location.search);
  if (shot) doc.classList.add("shot");
  if (shot) document.querySelectorAll("img[loading=lazy]").forEach(function (i) { i.loading = "eager"; });
  var reduceMotion = shot || window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Intro loader: once per browser session ----------
  var loader = document.querySelector(".loader");
  if (loader) {
    var seen = false;
    try { seen = sessionStorage.getItem("introSeen") === "1"; } catch (e) {}
    if (seen || reduceMotion) {
      loader.remove();
    } else {
      try { sessionStorage.setItem("introSeen", "1"); } catch (e) {}
      var start = Date.now();
      var hide = function () {
        setTimeout(function () {
          loader.classList.add("done");
          setTimeout(function () { loader.remove(); }, 800);
        }, Math.max(0, 1500 - (Date.now() - start)));
      };
      if (document.readyState === "complete") hide(); else window.addEventListener("load", hide);
      setTimeout(hide, 4000); // never block the page on a slow asset
    }
  }

  // ---------- Mobile menu ----------
  var toggle = document.querySelector(".menu-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = doc.classList.toggle("menu-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    document.querySelectorAll(".mobile-menu a").forEach(function (a) {
      a.addEventListener("click", function () { doc.classList.remove("menu-open"); });
    });
  }

  // ---------- Project filters ----------
  document.querySelectorAll(".filters").forEach(function (group) {
    var grid = group.parentElement.querySelector("[data-filter-grid]");
    if (!grid) return;
    group.addEventListener("click", function (e) {
      var btn = e.target.closest(".filter");
      if (!btn) return;
      var f = btn.getAttribute("data-filter");
      group.querySelectorAll(".filter").forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      grid.querySelectorAll(".work-card").forEach(function (card) {
        card.hidden = f !== "all" && card.getAttribute("data-category") !== f;
        if (!card.hidden) card.classList.add("in");
      });
    });
  });

  // ---------- Glowing ribbons (background canvas) ----------
  var canvas = document.querySelector(".glow-canvas");
  var scrollY = window.scrollY;
  var pointer = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5, px: -9999, py: -9999, tpx: -9999, tpy: -9999, on: 0 };
  var ripples = [];
  if (canvas && canvas.getContext) {
    var ctx = canvas.getContext("2d");
    var W = 0, H = 0, dpr = 1;
    // palette: peach, coral, crimson, plum
    var ribbons = [
      { rgb: "208,85,90", y: 0.30, amp: 0.16, freq: 1.6, speed: 0.00022, phase: 0.0, strands: 26, spread: 1.2, alpha: 0.26 },
      { rgb: "164,40,64", y: 0.62, amp: 0.20, freq: 1.2, speed: 0.00016, phase: 2.1, strands: 30, spread: 1.5, alpha: 0.28 },
      { rgb: "255,200,169", y: 0.45, amp: 0.10, freq: 2.2, speed: 0.00028, phase: 4.2, strands: 16, spread: 0.8, alpha: 0.16 },
      { rgb: "120,128,160", y: 0.80, amp: 0.14, freq: 1.0, speed: 0.00012, phase: 1.3, strands: 20, spread: 1.7, alpha: 0.20 }
    ];

    var resize = function () {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", function (e) {
      pointer.tx = e.clientX / W; pointer.ty = e.clientY / H;
      pointer.tpx = e.clientX; pointer.tpy = e.clientY;
      if (pointer.px < -999) { pointer.px = e.clientX; pointer.py = e.clientY; }
      pointer.on = 1;
    }, { passive: true });
    document.addEventListener("pointerleave", function () { pointer.on = 0; });
    // A click or tap sends a ripple through the ribbons.
    window.addEventListener("pointerdown", function (e) {
      ripples.push({ x: e.clientX, y: e.clientY, t: performance.now() });
      if (ripples.length > 4) ripples.shift();
    }, { passive: true });

    var draw = function (t) {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      pointer.x += (pointer.tx - pointer.x) * 0.04;
      pointer.y += (pointer.ty - pointer.y) * 0.04;
      pointer.px += (pointer.tpx - pointer.px) * 0.12;
      pointer.py += (pointer.tpy - pointer.py) * 0.12;
      ripples = ripples.filter(function (rp) { return t - rp.t < 2200; });
      var reach = Math.min(W, H) * 0.18;             // how far the cursor's pull extends
      var scroll = scrollY * 0.0012;
      var steps = Math.max(40, Math.round(W / 22));

      ribbons.forEach(function (r, ri) {
        var cy = H * (r.y + 0.12 * Math.sin(scroll + r.phase) + (pointer.y - 0.5) * 0.08);
        for (var s = 0; s < r.strands; s++) {
          var k = s / (r.strands - 1) - 0.5;          // -0.5 .. 0.5 across the ribbon
          var edge = 1 - Math.abs(k) * 1.6;            // strands fade toward the edges
          if (edge <= 0) continue;
          ctx.beginPath();
          for (var i = 0; i <= steps; i++) {
            var u = i / steps;
            var x = -0.05 * W + u * 1.1 * W;
            var twist = Math.sin(u * 3.2 + t * r.speed * 1.7 + r.phase + scroll * 0.6);
            var y = cy
              + H * r.amp * Math.sin(u * Math.PI * r.freq + t * r.speed + r.phase + scroll)
              + H * r.amp * 0.35 * Math.sin(u * Math.PI * r.freq * 2.3 - t * r.speed * 1.3 + ri)
              + k * r.spread * 60 * twist
              + (pointer.x - 0.5) * 40 * Math.sin(u * Math.PI);
            // Cursor: strands nearby bend towards it.
            if (pointer.on) {
              var dx = x - pointer.px, dy = y - pointer.py;
              var pull = Math.exp(-(dx * dx + dy * dy) / (2 * reach * reach));
              y += (pointer.py - y) * 0.35 * pull;
            }
            // Ripples: an expanding ring that displaces strands as it passes.
            for (var q = 0; q < ripples.length; q++) {
              var rp = ripples[q], age = t - rp.t;
              if (age < 0) continue;
              var dist = Math.sqrt((x - rp.x) * (x - rp.x) + (y - rp.y) * (y - rp.y));
              var front = dist - age * 0.7;
              y += Math.exp(-(front * front) / 3200) * Math.exp(-age / 900) * 34 * Math.sin(dist * 0.045);
            }
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.strokeStyle = "rgba(" + r.rgb + "," + (r.alpha * edge).toFixed(3) + ")";
          ctx.lineWidth = s % 5 === 0 ? 1.6 : 0.8;
          ctx.stroke();
        }
      });
      ctx.globalCompositeOperation = "source-over";
    };

    var running = true;
    var loop = function (t) {
      if (!running) return;
      draw(t);
      requestAnimationFrame(loop);
    };
    if (reduceMotion) {
      draw(0);
      window.addEventListener("resize", function () { draw(0); });
    } else {
      requestAnimationFrame(loop);
      document.addEventListener("visibilitychange", function () {
        running = !document.hidden;
        if (running) requestAnimationFrame(loop);
      });
    }
  }


  // ---------- Card hover previews: cycle through screens from the case study ----------
  if (!reduceMotion && window.matchMedia("(hover: hover)").matches) {
    document.querySelectorAll("[data-previews]").forEach(function (media) {
      var list = (media.getAttribute("data-previews") || "").split("|").filter(Boolean);
      if (!list.length) return;
      var card = media.closest("a") || media;
      var layer = null, timer = null, idx = -1;
      function show() {
        idx = (idx + 1) % list.length;
        var next = document.createElement("img");
        next.className = "preview-frame"; next.alt = ""; next.src = list[idx];
        next.onload = function () {
          if (!timer) return;
          layer.appendChild(next);
          void next.offsetWidth;            // commit the start state so the fade runs
          next.classList.add("on");
          var old = layer.querySelectorAll(".preview-frame");
          if (old.length > 2) old[0].remove();
        };
      }
      card.addEventListener("pointerenter", function () {
        if (!layer) { layer = document.createElement("div"); layer.className = "preview-layer"; media.appendChild(layer); }
        layer.classList.add("on");
        show(); timer = setInterval(show, 1100);
      });
      card.addEventListener("pointerleave", function () {
        clearInterval(timer); timer = null; idx = -1;
        if (layer) { layer.classList.remove("on"); layer.innerHTML = ""; }
      });
    });
  }

  // ---------- Try-it quiz ----------
  document.querySelectorAll("[data-quiz]").forEach(function (quiz) {
    var opts = quiz.querySelectorAll(".quiz-opt");
    var expl = quiz.querySelector(".quiz-expl");
    var result = quiz.querySelector(".quiz-result");
    opts.forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (quiz.classList.contains("answered")) return;
        quiz.classList.add("answered");
        var right = btn.getAttribute("data-correct") === "1";
        btn.classList.add(right ? "is-right" : "is-wrong");
        opts.forEach(function (o) { if (o.getAttribute("data-correct") === "1") o.classList.add("is-right"); o.disabled = true; });
        result.textContent = right ? "Correct — nicely done." : "Not quite — here’s the trick.";
        expl.hidden = false;
      });
    });
    quiz.querySelector(".quiz-reset").addEventListener("click", function () {
      quiz.classList.remove("answered"); expl.hidden = true;
      opts.forEach(function (o) { o.classList.remove("is-right", "is-wrong"); o.disabled = false; });
      opts[0].focus();
    });
  });

  // ---------- Command palette (⌘K / Ctrl+K) ----------
  var palette = document.querySelector(".palette");
  if (palette && window.__INDEX) {
    var input = palette.querySelector(".palette-input");
    var listEl = palette.querySelector(".palette-list");
    var items = window.__INDEX, shown = [], active = 0, lastFocus = null;
    var esc = function (t) { return t.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    function render() {
      var q = input.value.trim().toLowerCase();
      shown = items.filter(function (it) { return !q || (it.t + " " + it.s).toLowerCase().indexOf(q) > -1; }).slice(0, 12);
      if (active >= shown.length) active = 0;
      listEl.innerHTML = shown.length ? shown.map(function (it, i) {
        return '<li role="option" aria-selected="' + (i === active) + '" data-i="' + i + '"><span>' + esc(it.t) + '</span><small>' + esc(it.s) + "</small></li>";
      }).join("") : '<li class="palette-empty">No matches</li>';
    }
    function go(it) {
      if (!it) return;
      if (it.x) window.open(it.u, "_blank", "noopener"); else location.href = it.u;
      close();
    }
    function open() {
      lastFocus = document.activeElement;
      palette.hidden = false; doc.classList.add("palette-open");
      input.value = ""; active = 0; render(); input.focus();
    }
    function close() {
      palette.hidden = true; doc.classList.remove("palette-open");
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); palette.hidden ? open() : close(); return; }
      if (palette.hidden) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(active + 1, shown.length - 1); render(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(active - 1, 0); render(); }
      else if (e.key === "Enter") { e.preventDefault(); go(shown[active]); }
    });
    input.addEventListener("input", function () { active = 0; render(); });
    listEl.addEventListener("click", function (e) { var li = e.target.closest("[data-i]"); if (li) go(shown[+li.getAttribute("data-i")]); });
    palette.addEventListener("click", function (e) { if (e.target === palette) close(); });
    document.querySelectorAll("[data-open-palette]").forEach(function (b) { b.addEventListener("click", open); });
    if (!/Mac|iPhone|iPad/.test(navigator.platform)) document.querySelectorAll(".search-btn kbd").forEach(function (k) { k.textContent = "Ctrl K"; });
  }

  // ---------- Click-to-zoom images in case studies ----------
  var lightbox = document.querySelector(".lightbox");
  if (lightbox) {
    var lbImg = lightbox.querySelector("img");
    document.querySelectorAll(".prose .shot img, .case-cover img").forEach(function (im) {
      im.classList.add("zoomable");
      im.addEventListener("click", function () {
        lbImg.src = im.currentSrc || im.src; lbImg.alt = im.alt;
        lightbox.hidden = false; doc.classList.add("lightbox-open");
      });
    });
    var closeLb = function () { lightbox.hidden = true; doc.classList.remove("lightbox-open"); };
    lightbox.addEventListener("click", closeLb);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !lightbox.hidden) closeLb(); });
  }

  // ---------- Live local time in Bangalore ----------
  var timeEls = document.querySelectorAll("[data-local-time]");
  if (timeEls.length) {
    var fmt = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" });
    var tick = function () {
      var now = fmt.format(new Date());
      timeEls.forEach(function (el) { el.textContent = (el.getAttribute("data-prefix") || "Local time ") + now + " IST"; });
    };
    tick(); setInterval(tick, 30000);
  }

  // ---------- Scroll-driven: header, progress, reveal, TOC ----------
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  var sections = tocLinks.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); });
  var progress = document.querySelector(".progress span");
  // Anything above the bottom of the viewport is revealed, so fast scrolling never leaves hidden gaps.
  var pending = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var ticking = false;

  function update() {
    ticking = false;
    scrollY = window.scrollY;
    var vh = window.innerHeight;
    if (header) header.classList.toggle("scrolled", scrollY > 12);

    if (progress) {
      var max = document.documentElement.scrollHeight - vh;
      progress.style.transform = "scaleX(" + (max > 0 ? Math.min(1, scrollY / max) : 0) + ")";
    }

    if (pending.length) {
      var limit = vh * 0.92;
      pending = pending.filter(function (el) {
        if (el.getBoundingClientRect().top < limit) { el.classList.add("in"); return false; }
        return true;
      });
    }

    if (sections.length) {
      var current = -1;
      sections.forEach(function (s, i) { if (s && s.getBoundingClientRect().top < vh * 0.3) current = i; });
      tocLinks.forEach(function (a, i) { a.classList.toggle("active", i === current); });
    }
  }
  function onScroll() {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  update();
})();
