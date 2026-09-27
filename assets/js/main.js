(function () {
  var doc = document.documentElement;
  var header = document.querySelector(".site-header");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
  var pointer = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
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
    }, { passive: true });

    var draw = function (t) {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      pointer.x += (pointer.tx - pointer.x) * 0.04;
      pointer.y += (pointer.ty - pointer.y) * 0.04;
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
