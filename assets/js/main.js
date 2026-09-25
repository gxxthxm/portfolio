(function () {
  // Mobile menu
  var nav = document.querySelector(".nav");
  var toggle = document.querySelector(".nav-toggle");
  if (nav && toggle) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
  }

  // Footer year
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  // Reveal on scroll. Anything at or above the bottom of the viewport is
  // revealed, so fast scrolling or jumping to an anchor never leaves hidden gaps.
  var pending = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var ticking = false;
  function check() {
    ticking = false;
    var limit = window.innerHeight * 0.95;
    pending = pending.filter(function (el) {
      if (el.getBoundingClientRect().top < limit) {
        el.classList.add("in");
        return false;
      }
      return true;
    });
    if (!pending.length) {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    }
  }
  function onScroll() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(check);
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  check();
})();
