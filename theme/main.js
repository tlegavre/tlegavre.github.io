// Dark-mode button: toggles light/dark and remembers the choice (otherwise: system setting).
for (const btn of document.querySelectorAll(".theme-toggle")) {
  btn.addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  });
}

// Rebuild the mailto link (the raw address is not written in the HTML).
for (const a of document.querySelectorAll("a.email[data-u][data-d]")) {
  a.href = "mailto:" + a.dataset.u + "@" + a.dataset.d;
}

(() => {
  const toc = document.querySelector(".toc");
  if (!toc) return;
  const links = [...toc.querySelectorAll("a")];

  // On mobile the menu is a scrollable tab bar: keep the active tab visible.
  function reveal(a) {
    if (toc.scrollWidth <= toc.clientWidth) return;
    const r = a.getBoundingClientRect(), t = toc.getBoundingClientRect();
    if (r.left < t.left || r.right > t.right) {
      toc.scrollBy({ left: r.left - t.left - 24, behavior: "smooth" });
    }
  }

  // Multi-page version: the active tab is already marked in the HTML.
  const current = toc.querySelector('[aria-current="page"]');
  if (current) { reveal(current); return; }

  // One-page version: highlight the section currently being read.
  const sections = links
    .map((a) => document.getElementById(decodeURIComponent(a.hash.slice(1))))
    .filter(Boolean);
  if (!sections.length) return;

  let active = null;
  let ticking = false;

  function setActive(id) {
    if (id === active) return;
    active = id;
    for (const a of links) {
      const on = a.hash === "#" + id;
      a.classList.toggle("active", on);
      if (on) { a.setAttribute("aria-current", "location"); reveal(a); }
      else a.removeAttribute("aria-current");
    }
  }

  function update() {
    ticking = false;
    const line = Math.min(window.innerHeight * 0.3, 240);
    let id = sections[0].id;
    for (const s of sections) {
      if (s.getBoundingClientRect().top <= line) id = s.id;
    }
    const atBottom =
      window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
    if (atBottom && window.scrollY > 0) id = sections[sections.length - 1].id;
    setActive(id);
  }

  window.addEventListener("scroll", () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  window.addEventListener("resize", update);
  update();
})();
