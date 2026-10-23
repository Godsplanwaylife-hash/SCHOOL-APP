/* ============================================================
   Home page animations - Good Foundation of Christ Group of School
   Plain JavaScript, no libraries.
   ============================================================ */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1. Scroll progress bar + back-to-top button ---------- */
  var progress = document.getElementById("progress");
  var toTop = document.getElementById("toTop");

  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    if (progress) progress.style.width = pct + "%";
    if (toTop) toTop.classList.toggle("show", window.scrollY > 600);
  }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  if (toTop) {
    toTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  /* ---------- 2. Floating school letters and numbers in the hero ---------- */
  var floaters = document.getElementById("floaters");
  if (floaters && !reduceMotion) {
    var symbols = ["A", "B", "C", "a", "b", "c", "1", "2", "3", "+", "=", "★", "✎", "?"];
    var count = window.innerWidth < 700 ? 12 : 22;
    for (var i = 0; i < count; i++) {
      var el = document.createElement("span");
      el.className = "floater";
      el.textContent = symbols[Math.floor(Math.random() * symbols.length)];
      el.style.setProperty("--x", Math.random() * 100 + "%");
      el.style.setProperty("--s", 22 + Math.random() * 46 + "px");
      el.style.setProperty("--t", 14 + Math.random() * 16 + "s");
      el.style.setProperty("--dl", -Math.random() * 30 + "s");
      floaters.appendChild(el);
    }
  }

  /* ---------- 3. Typewriter line in the hero ---------- */
  var typed = document.getElementById("typed");
  if (typed && !reduceMotion) {
    var words = ["faith.", "knowledge.", "curiosity.", "good character.", "excellence."];
    var w = 0, c = 0, deleting = false;

    (function tick() {
      var word = words[w];
      typed.textContent = word.slice(0, c);

      var delay = deleting ? 45 : 95;
      if (!deleting && c === word.length) { deleting = true; delay = 1500; }
      else if (deleting && c === 0) { deleting = false; w = (w + 1) % words.length; delay = 350; }
      else { c += deleting ? -1 : 1; }

      setTimeout(tick, delay);
    })();
  }

  /* ---------- 4. Counting numbers (start when scrolled into view) ---------- */
  var counters = document.querySelectorAll("[data-count]");

  function runCounter(el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0;
    if (reduceMotion || target === 0) { el.textContent = target; return; }
    var duration = 1700;
    var start = null;

    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  if ("IntersectionObserver" in window) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { runCounter(e.target); co.unobserve(e.target); }
      });
    }, { threshold: 0.6 });
    counters.forEach(function (el) { co.observe(el); });
  } else {
    counters.forEach(function (el) { el.textContent = el.getAttribute("data-count"); });
  }

  /* ---------- 5. Crest tilts towards the mouse ---------- */
  var hero = document.querySelector(".hero");
  var crest = document.querySelector(".crest-wrap");
  var canHover = window.matchMedia && window.matchMedia("(hover: hover)").matches;

  if (hero && crest && canHover && !reduceMotion) {
    hero.addEventListener("mousemove", function (e) {
      var r = hero.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      crest.style.transform = "perspective(900px) rotateY(" + x * 16 + "deg) rotateX(" + -y * 16 + "deg)";
    });
    hero.addEventListener("mouseleave", function () {
      crest.style.transform = "";
    });
  }

  /* ---------- 6. FAQ: open one question at a time ---------- */
  var faqs = document.querySelectorAll(".faq-item");
  faqs.forEach(function (item) {
    item.addEventListener("toggle", function () {
      if (item.open) {
        faqs.forEach(function (other) { if (other !== item) other.open = false; });
      }
    });
  });

  /* ---------- 7. Confetti burst in school colours ---------- */
  function burst(x, y) {
    if (reduceMotion || !document.body.animate) return;
    var colours = ["#c8102e", "#0b1f4b", "#ffffff", "#ff5a73", "#1c3a7a"];
    for (var i = 0; i < 28; i++) {
      var p = document.createElement("span");
      p.className = "confetti";
      p.style.left = x + "px";
      p.style.top = y + "px";
      p.style.background = colours[i % colours.length];
      document.body.appendChild(p);

      var angle = Math.random() * Math.PI * 2;
      var dist = 70 + Math.random() * 110;
      var dx = Math.cos(angle) * dist;
      var dy = Math.sin(angle) * dist - 40;

      var anim = p.animate([
        { transform: "translate(0,0) rotate(0deg)", opacity: 1 },
        { transform: "translate(" + dx + "px," + (dy + 120) + "px) rotate(" + (Math.random() * 720 - 360) + "deg)", opacity: 0 }
      ], { duration: 900 + Math.random() * 500, easing: "cubic-bezier(.2,.8,.3,1)" });
      anim.onfinish = (function (node) { return function () { node.remove(); }; })(p);
    }
  }

  document.querySelectorAll("[data-confetti]").forEach(function (btn) {
    btn.addEventListener("click", function (e) { burst(e.clientX, e.clientY); });
  });
})();