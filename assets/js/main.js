(function () {
  var doc = document.documentElement;
  var header = document.querySelector(".site-header");
  // "?shot" renders a still page for mockup screenshots: no intro, no motion.
  var shot = /[?&]shot\b/.test(location.search);
  if (shot) doc.classList.add("shot");
  if (shot) document.querySelectorAll("img[loading=lazy]").forEach(function (i) { i.loading = "eager"; });
  var reduceMotion = shot || window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Intro: "hello" in many languages, once per browser session ----------
  var loader = document.querySelector(".loader");
  if (loader) {
    var seen = false;
    try { seen = sessionStorage.getItem("introSeen") === "1"; } catch (e) {}
    if (seen || reduceMotion) {
      loader.remove();
    } else {
      try { sessionStorage.setItem("introSeen", "1"); } catch (e) {}
      var wordEl = loader.querySelector(".loader-word");
      var greetings = [];
      try { greetings = JSON.parse(wordEl.getAttribute("data-greetings")); } catch (e) {}
      var finished = false, loaded = document.readyState === "complete";
      var hide = function () {
        if (!finished || !loaded || loader.classList.contains("done")) return;
        loader.classList.add("done");
        setTimeout(function () { loader.remove(); }, 700);
      };
      window.addEventListener("load", function () { loaded = true; hide(); });
      setTimeout(function () { loaded = true; finished = true; hide(); }, 5000); // never block on a slow asset
      var n = 0;
      var step = function () {
        var g = greetings[n];
        if (!g) { finished = true; hide(); return; }
        wordEl.textContent = g[0];
        wordEl.setAttribute("lang", g[1]);
        wordEl.classList.remove("flash"); void wordEl.offsetWidth; wordEl.classList.add("flash");
        var last = n === greetings.length - 1;
        wordEl.classList.toggle("final", last);
        n++;
        // Linger on the first "Hello", flash through the rest, then hold the name.
        setTimeout(step, n === 1 ? 420 : last ? 900 : 150);
      };
      step();
    }
  }

  // ---------- Hero: rotating accent word ----------
  var rotator = document.querySelector(".rotator");
  if (rotator && !reduceMotion) {
    var rWords = rotator.getAttribute("data-words").split("|");
    var rEl = rotator.querySelector(".rotator-word");
    var ri = 0;
    setInterval(function () {
      if (document.hidden) return;
      rEl.classList.add("out");
      setTimeout(function () {
        ri = (ri + 1) % rWords.length;
        rEl.textContent = rWords[ri];
        rEl.classList.remove("out");
      }, 280);
    }, 2400);
  }

  // ---------- Stats count up when they come into view ----------
  var counters = Array.prototype.slice.call(document.querySelectorAll("[data-count]"));
  var countUp = function (el) {
    var text = el.textContent, m = text.match(/(\d+(?:\.\d+)?)(?!.*\d)/);   // last number in the string
    if (!m || reduceMotion) return;
    var target = parseFloat(m[1]), before = text.slice(0, m.index), after = text.slice(m.index + m[1].length);
    var t0 = performance.now(), dur = 1300;
    var frame = function (now) {
      var k = Math.min(1, (now - t0) / dur), eased = 1 - Math.pow(1 - k, 3);
      el.textContent = before + Math.round(target * eased) + after;
      if (k < 1) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  };

  // ---------- A small wave when you switch tabs ----------
  var baseTitle = document.title;
  document.addEventListener("visibilitychange", function () {
    document.title = document.hidden ? "👋 Come back soon — Gauthem" : baseTitle;
  });

  // ---------- Mobile menu ----------
  var toggle = document.querySelector(".menu-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = doc.classList.toggle("menu-open");
      if (typeof lockScroll === "function") lockScroll(open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    document.querySelectorAll(".mobile-menu a").forEach(function (a) {
      a.addEventListener("click", function () { doc.classList.remove("menu-open"); if (typeof lockScroll === "function") lockScroll(false); });
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



  // ---------- Smooth scrolling ----------
  var lenis = null;
  var headerOffset = function () { return -((header && header.offsetHeight) || 72) - 16; };
  if (window.Lenis && !reduceMotion) {
    lenis = new window.Lenis({ lerp: 0.09, wheelMultiplier: 1, smoothWheel: true });
    window.__lenis = lenis;   // handy for debugging in the console
    var lraf = function (t) { lenis.raf(t); requestAnimationFrame(lraf); };
    requestAnimationFrame(lraf);
  }
  // In-page links glide to their target (and keep the URL hash).
  document.addEventListener("click", function (e) {
    var a = e.target.closest('a[href*="#"]');
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey) return;
    var url = new URL(a.href, location.href);
    if (url.pathname !== location.pathname || !url.hash) return;
    var target = url.hash === "#main" ? 0 : document.getElementById(decodeURIComponent(url.hash.slice(1)));
    if (target === null) return;
    e.preventDefault();
    if (lenis) lenis.scrollTo(target, { offset: target === 0 ? 0 : headerOffset(), duration: 1.2 });
    else window.scrollTo({ top: target === 0 ? 0 : target.getBoundingClientRect().top + window.scrollY + headerOffset(), behavior: reduceMotion ? "auto" : "smooth" });
    history.replaceState(null, "", url.hash);
  });
  var lockScroll = function (on) { if (lenis) { on ? lenis.stop() : lenis.start(); } };

  // ---------- Page transitions: fallback for browsers without View Transitions ----------
  if (doc.classList.contains("no-vt") && !reduceMotion) {
    document.addEventListener("click", function (e) {
      var a = e.target.closest("a[href]");
      if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (a.target === "_blank" || a.hasAttribute("download")) return;
      var url = new URL(a.href, location.href);
      if (url.origin !== location.origin || (url.pathname === location.pathname && url.hash)) return;
      if (/\.(pdf|jpg|png|mp4)$/i.test(url.pathname)) return;
      e.preventDefault();
      doc.classList.add("leaving");
      setTimeout(function () { location.href = url.href; }, 240);
    });
    window.addEventListener("pageshow", function () { doc.classList.remove("leaving"); });
  }

  // ---------- Staggered reveals and parallax ----------
  document.querySelectorAll(".work-grid, .features, .services-grid, .toolkit, .contact-grid, .edu-grid, .exp-list, .stats").forEach(function (group) {
    var kids = group.querySelectorAll(":scope > .reveal");
    kids.forEach(function (el, i) {
      el.style.setProperty("--d", Math.min(i % 6, 5) * 80 + "ms");
      // drop the delay once revealed, so hover effects stay instant
      el.addEventListener("transitionend", function clear() { el.style.removeProperty("--d"); el.removeEventListener("transitionend", clear); });
    });
  });
  var parallax = reduceMotion ? [] : Array.prototype.slice.call(document.querySelectorAll(".feature-media > img, .case-cover img, .next-media img"));
  parallax.forEach(function (im) { im.classList.add("parallax"); });

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
      palette.hidden = false; doc.classList.add("palette-open"); lockScroll(true);
      input.value = ""; active = 0; render(); input.focus();
    }
    function close() {
      palette.hidden = true; doc.classList.remove("palette-open"); lockScroll(false);
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
        lightbox.hidden = false; doc.classList.add("lightbox-open"); lockScroll(true);
      });
    });
    var closeLb = function () { lightbox.hidden = true; doc.classList.remove("lightbox-open"); lockScroll(false); };
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

    if (parallax.length) {
      for (var pi = 0; pi < parallax.length; pi++) {
        var r = parallax[pi].parentElement.getBoundingClientRect();
        if (r.bottom < 0 || r.top > vh) continue;
        var prog = (r.top + r.height / 2 - vh / 2) / vh;       // -0.5 .. 0.5 while on screen
        parallax[pi].style.setProperty("--py", (prog * -48).toFixed(1) + "px");
      }
    }

    if (counters.length) {
      counters = counters.filter(function (el) {
        if (el.getBoundingClientRect().top < vh * 0.9) { countUp(el); return false; }
        return true;
      });
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
