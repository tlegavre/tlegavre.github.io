#!/usr/bin/env python3
"""
Personal website generator.

    python3 build.py            build the site into public/
    python3 build.py serve      build, serve on http://localhost:8000
                                and rebuild on every change

Content: content.yml        Look: theme/        Files: static/
Dependencies: PyYAML and Jinja2  (pip install -r requirements.txt)
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import yaml
    from jinja2 import Environment, FileSystemLoader, pass_context
    from markupsafe import Markup, escape
except ImportError as exc:
    sys.exit(f"Missing module: {exc.name}. Install with: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content.yml"
THEME = ROOT / "theme"
STATIC = ROOT / "static"
OUT = ROOT / "public"

BUILTIN_SECTIONS = ["about", "news", "publications", "presentations", "events", "software", "teaching"]
PUB_KINDS = ["preprint", "published", "conference", "journal", "workshop", "thesis", "other"]

LABELS = {
    "about": {"en": "About", "fr": "À propos"},
    "news": {"en": "News", "fr": "Actualités"},
    "publications": {"en": "Publications", "fr": "Publications"},
    "presentations": {"en": "Presentations", "fr": "Présentations"},
    "talks": {"en": "Talks", "fr": "Exposés"},
    "posters": {"en": "Posters", "fr": "Posters"},
    "events": {"en": "Events Attended", "fr": "Événements"},
    "software": {"en": "Software", "fr": "Logiciels"},
    "teaching": {"en": "Teaching", "fr": "Enseignement"},
    "links": {"en": "Links", "fr": "Liens"},
    "contact": {"en": "Contact", "fr": "Contact"},
    "theme": {"en": "Toggle dark mode", "fr": "Basculer le mode nuit"},
    "with": {"en": "with", "fr": "avec"},
    "and": {"en": "and", "fr": "et"},
    "older_news": {"en": "Older news", "fr": "Actualités plus anciennes"},
    "updated": {"en": "Last updated", "fr": "Dernière mise à jour"},
    "menu": {"en": "Sections", "fr": "Sections"},
    "language": {"en": "Language", "fr": "Langue"},
    "skip": {"en": "Skip to content", "fr": "Aller au contenu"},
    "slides": {"en": "slides", "fr": "transparents"},
    "video": {"en": "video", "fr": "vidéo"},
    "code": {"en": "code", "fr": "code"},
    "cosupervised": {"en": "co-supervised with", "fr": "en co-encadrement avec"},
    "kind_preprint": {"en": "Preprints", "fr": "Prépublications"},
    "kind_published": {"en": "Published Papers", "fr": "Articles publiés"},
    "kind_journal": {"en": "Journal papers", "fr": "Articles de revues"},
    "kind_conference": {"en": "Conference papers", "fr": "Articles de conférences"},
    "kind_workshop": {"en": "Workshops", "fr": "Ateliers"},
    "kind_thesis": {"en": "Theses", "fr": "Thèses et mémoires"},
    "kind_other": {"en": "Other", "fr": "Autres"},
    "year_undated": {"en": "Undated", "fr": "Non daté"},
}

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
}

ICONS = {
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
            '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "trophy": '<path d="M7.2 5H4.6a.6.6 0 0 0-.6.6v1.1A4 4 0 0 0 7.7 10.7" fill="none" stroke="#8b8f96" stroke-width="1.6"/>'
              '<path d="M16.8 5h2.6a.6.6 0 0 1 .6.6v1.1a4 4 0 0 1-3.7 4" fill="none" stroke="#8b8f96" stroke-width="1.6"/>'
              '<path d="M6.8 3h10.4v5.6a5.2 5.2 0 0 1-10.4 0z" fill="url(#silver)" stroke="#7d8188" stroke-width=".9"/>'
              '<path d="M10.9 13.6h2.2v3.6h-2.2z" fill="url(#silver)" stroke="#7d8188" stroke-width=".7"/>'
              '<path d="M8.2 17.4h7.6a.8.8 0 0 1 .8.8v2.2H7.4v-2.2a.8.8 0 0 1 .8-.8z" fill="url(#silver)" stroke="#7d8188" stroke-width=".9"/>'
              '<path d="M9.2 4.6v3.6" stroke="#fff" stroke-width="1.1" stroke-linecap="round" opacity=".8"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6'
             'A19.8 19.8 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81'
             'a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57'
             ' 2.81.7A2 2 0 0 1 22 16.92z"/>',
}


BRANDS = {
    "github": ('0 0 16 16', '<path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 '
               '5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23'
               '-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33'
               '.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36'
               '-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 '
               '2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 '
               '3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 '
               '16 8c0-4.42-3.58-8-8-8z"/>'),
    "linkedin": ('0 0 24 24', '<rect x="1.5" y="1.5" width="21" height="21" rx="3.5" fill="#0A66C2"/>'
                 '<g fill="#fff"><circle cx="7.1" cy="7.2" r="1.75"/><rect x="5.6" y="9.6" width="3" height="8.6"/>'
                 '<path d="M10.9 9.6h2.9v1.25c.45-.8 1.5-1.5 3-1.5 2.6 0 3.4 1.6 3.4 4.1v4.75h-3v-4.2'
                 'c0-1.1-.2-2.1-1.5-2.1s-1.8.9-1.8 2.1v4.2h-3z"/></g>'),
    "orcid": ('0 0 24 24', '<circle cx="12" cy="12" r="11" fill="#A6CE39"/><g fill="#fff">'
              '<circle cx="7.7" cy="6.9" r="1.1"/><rect x="6.85" y="8.9" width="1.7" height="8.4"/>'
              '<path fill-rule="evenodd" d="M10.6 8.9h3.6c3.1 0 4.7 2 4.7 4.2s-1.6 4.2-4.7 4.2h-3.6z'
              'M12.3 10.4v5.4h1.8c2 0 3-1.2 3-2.7s-1-2.7-3-2.7z"/></g>'),
    "google scholar": ('0 0 24 24', '<circle cx="12" cy="16.4" r="6.2" fill="#8AB4F8"/>'
                       '<path d="M12 1.2 23.4 8.6 12 16 .6 8.6z" fill="#4285F4"/>'
                       '<path d="M19.6 10.8v5.2" stroke="#4285F4" stroke-width="1.4" stroke-linecap="round"/>'),
}


def brand_icon(name) -> Markup | None:
    entry = BRANDS.get(str(name or "").strip().lower())
    if not entry:
        return None
    viewbox, body = entry
    return Markup(f'<svg class="brand" viewBox="{viewbox}" aria-hidden="true">{body}</svg>')


class BuildError(Exception):
    pass


class _Loader(yaml.SafeLoader):
    pass


_Loader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers
          if tag not in ("tag:yaml.org,2002:float", "tag:yaml.org,2002:timestamp")]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_content() -> dict:
    try:
        data = yaml.load(CONTENT.read_text(encoding="utf-8"), Loader=_Loader) or {}
    except FileNotFoundError:
        raise BuildError(f"File not found: {CONTENT}")
    except yaml.YAMLError as exc:
        raise BuildError(
            f"Syntax error in content.yml:\n{exc}\n\n"
            "Tip: quote any text that starts with * [ ` "
            "or contains ': '."
        )
    if not isinstance(data, dict):
        raise BuildError("content.yml must contain sections (site:, person:, ...).")
    return data


def localize(obj, lang: str, langs: list[str]):
    """Replace every {en: ..., fr: ...} with the value for the requested language."""
    if isinstance(obj, dict):
        if obj and (set(obj) <= set(langs)
                    or all(isinstance(k, str) and re.fullmatch(r"[a-z]{2}", k) for k in obj)):
            for key in (lang, langs[0], *obj):
                if obj.get(key) not in (None, ""):
                    return localize(obj[key], lang, langs)
            return ""
        return {k: localize(v, lang, langs) for k, v in obj.items()}
    if isinstance(obj, list):
        return [localize(x, lang, langs) for x in obj]
    return obj


_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITAL = re.compile(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])")
_BULLET = re.compile(r"^\s*[-*]\s+")


def rel_url(url, root: str = "") -> str:
    """Prefix relative links (files/cv.pdf...) so they also work from sub-folders."""
    url = "" if url is None else str(url)
    if not url or re.match(r"^([a-z][a-z0-9+.-]*:|/|#)", url, re.I):
        return url
    return root + url


def md_inline(text, root: str = "") -> Markup:
    if text is None or text == "":
        return Markup("")
    if isinstance(text, Markup):
        return text
    stash: list[str] = []

    def keep(fragment: str) -> str:
        stash.append(fragment)
        return f"\x00{len(stash) - 1}\x00"

    s = str(text)
    s = _CODE.sub(lambda m: keep(f"<code>{html.escape(m[1])}</code>"), s)
    s = _LINK.sub(lambda m: keep(f'<a href="{html.escape(rel_url(m[2], root), quote=True)}">')
                  + m[1] + keep("</a>"), s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITAL.sub(r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m[1])], s)
    return Markup(s)


def md_block(text, root: str = "") -> Markup:
    if not text:
        return Markup("")
    out = []
    for block in re.split(r"\n\s*\n", str(text).strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if block.lstrip().startswith("<"):
            out.append(block.strip())
        elif all(_BULLET.match(l) for l in lines):
            items = "".join(f"<li>{md_inline(_BULLET.sub('', l), root)}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{md_inline(' '.join(l.strip() for l in lines), root)}</p>")
    return Markup("\n".join(out))


def plain(text) -> str:
    """Plain text (for <meta> tags)."""
    s = re.sub(r"<[^>]+>", "", str(md_inline(text)))
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def fmt_date(value, lang: str, *, full_ok: bool = True) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (dt.date, dt.datetime)):
        y, m, d = value.year, value.month, value.day
    else:
        mt = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", str(value).strip())
        if not mt:
            return str(value)
        y, m, d = int(mt[1]), int(mt[2]), int(mt[3]) if mt[3] else None
    if not 1 <= m <= 12:
        return str(value)
    month = MONTHS.get(lang, MONTHS["en"])[m - 1]
    if d and full_ok:
        if lang == "fr":
            return f"{'1er' if d == 1 else d} {month} {y}"
        return f"{month} {d}, {y}"
    return f"{month[:1].upper()}{month[1:]} {y}"


def join_names(names, lang: str, and_word: str) -> str:
    if isinstance(names, str):
        names = [names]
    names = [str(n) for n in names or [] if n]
    if len(names) <= 2:
        return f" {and_word} ".join(names)
    last_sep = f", {and_word} " if lang == "en" else f" {and_word} "
    return ", ".join(names[:-1]) + last_sep + names[-1]


def year_of(item) -> int:
    m = re.match(r"\s*(\d{4})", str(item.get("year") or item.get("date") or ""))
    return int(m[1]) if m else 0


def extra_links(item: dict, L: dict) -> list[dict]:
    links = []

    def add(label, url):
        if url and label:
            links.append({"label": str(label), "url": str(url)})

    if item.get("eprint"):
        add(f"ePrint {item['eprint']}", f"https://eprint.iacr.org/{item['eprint']}")
    if item.get("doi"):
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", str(item["doi"]))
        add("DOI", f"https://doi.org/{doi}")
    if item.get("arxiv"):
        add(f"arXiv:{item['arxiv']}", f"https://arxiv.org/abs/{item['arxiv']}")
    if item.get("hal"):
        hal = str(item["hal"])
        add("HAL", hal if hal.startswith("http") else f"https://hal.science/{hal}")
    add("PDF", item.get("pdf"))
    add(L["slides"], item.get("slides"))
    add(L["video"], item.get("video"))
    add(L["code"], item.get("code"))
    for extra in item.get("links") or []:
        if isinstance(extra, dict):
            add(extra.get("label"), extra.get("url"))
    return links


class Section:
    def __init__(self, sid: str, kind: str, title: str, data: dict, entries: list):
        self.id, self.kind, self.title, self.data, self.entries = sid, kind, title, data, entries
        self.groups: list[dict] = []
        self.in_menu = not (isinstance(data, dict) and data.get("in_menu") is False)


def as_section_data(raw) -> tuple[dict, list]:
    if raw is None:
        return {}, []
    if isinstance(raw, list):
        return {}, raw
    if isinstance(raw, dict):
        return raw, list(raw.get("items") or [])
    if isinstance(raw, str):
        return {"text": raw}, []
    raise BuildError(f"Format de section non reconnu : {raw!r}")


def prepare_publications(sec: Section, lang: str, L: dict, root: str) -> None:
    pubs = []
    for p in sec.entries:
        if not isinstance(p, dict) or not p.get("title"):
            print(f"  ! publication skipped (no title): {p!r}", file=sys.stderr)
            continue
        meta = [md_inline(p["venue"], root)] if p.get("venue") else []
        if p.get("year") and str(p["year"]) not in str(p.get("venue") or ""):
            meta.append(escape(str(p["year"])))
        kind = p.get("kind") or "other"
        if kind not in PUB_KINDS:
            print(f"  ! unknown kind '{kind}' for '{p['title']}' -> other", file=sys.stderr)
            kind = "other"
        pubs.append({
            "title": p["title"], "url": p.get("url"), "kind": kind, "year": year_of(p),
            "with": join_names(p.get("with"), lang, L["and"]),
            "meta": Markup(", ").join(meta), "note": p.get("note"),
            "venue": md_inline(p["venue"], root) if p.get("venue") else None,
            "year_txt": "" if not p.get("year") or str(p["year"]) in str(p.get("venue") or "") else str(p["year"]),
            "links": extra_links(p, L),
        })
    pubs.sort(key=lambda p: -p["year"])

    mode = sec.data.get("group_by", "kind")
    if mode == "year":
        undated = [p for p in pubs if not p["year"]]
        years = sorted({p["year"] for p in pubs if p["year"]}, reverse=True)
        head = []
        if undated:
            kinds = {p["kind"] for p in undated}
            title = L[f"kind_{kinds.pop()}"] if len(kinds) == 1 else L["year_undated"]
            head = [{"title": title, "entries": undated}]
        sec.groups = [{"title": str(y), "entries": [p for p in pubs if p["year"] == y]} for y in years] + head
    elif mode == "none":
        sec.groups = [{"title": "", "entries": pubs}]
    else:
        order = sec.data.get("order") or PUB_KINDS
        sec.groups = [{"title": L[f"kind_{k}"], "entries": [p for p in pubs if p["kind"] == k]}
                      for k in order if k in PUB_KINDS]
    sec.groups = [g for g in sec.groups if g["entries"]]


def prepare_presentations(sec: Section, L: dict) -> None:
    """Talks then Posters subsections; each title has its list of venues."""
    for key in ("talks", "posters"):
        entries = [e for e in sec.data.get(key) or [] if isinstance(e, dict) and e.get("title")]
        for e in entries:
            venues = e.get("venues") or []
            if isinstance(venues, dict):
                venues = [venues]
            e["venues"] = [v for v in venues if isinstance(v, dict)]
            for v in e["venues"]:
                v["all_links"] = extra_links(v, L)
        if entries:
            sec.groups.append({"title": L[key], "entries": entries})


def build_sections(content: dict, site: dict, lang: str, L: dict, root: str) -> list[Section]:
    custom = content.get("custom") or {}
    sections = []
    for sid in site.get("sections") or BUILTIN_SECTIONS:
        if sid in BUILTIN_SECTIONS:
            if content.get(sid) is None:
                print(f"  ! section '{sid}' listed but missing from content.yml: skipped", file=sys.stderr)
                continue
            data, entries = as_section_data(content[sid])
            sec = Section(sid, sid, data.get("title") or L[sid], data, entries)
            if sid == "publications":
                prepare_publications(sec, lang, L, root)
            elif sid == "presentations":
                prepare_presentations(sec, L)
            elif sid in ("software", "teaching", "events"):
                for e in entries:
                    if isinstance(e, dict):
                        e["all_links"] = extra_links(e, L)
            sections.append(sec)
        elif sid in custom:
            data = custom[sid] or {}
            sections.append(Section(sid, "custom", data.get("title") or sid, data, []))
        else:
            raise BuildError(
                f"Unknown section '{sid}' in site.sections.\n"
                f"Available sections: {', '.join(BUILTIN_SECTIONS + list(custom))}"
            )
    return sections


def build(quiet: bool = False) -> None:
    raw = load_content()
    langs = [str(l) for l in (raw.get("site") or {}).get("languages") or ["en"]]
    prefix = {l: "" if i == 0 else f"{l}/" for i, l in enumerate(langs)}
    today = dt.date.today()
    version = int(time.time())

    env = Environment(loader=FileSystemLoader(str(THEME)), autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["md"] = pass_context(lambda ctx, v: md_block(v, ctx["root"]))
    env.filters["mdi"] = pass_context(lambda ctx, v: md_inline(v, ctx["root"]))
    env.filters["url"] = pass_context(lambda ctx, v: rel_url(v, ctx["root"]))
    env.filters["names"] = pass_context(lambda ctx, v: join_names(v, ctx["lang"], ctx["L"]["and"]))
    env.filters["date"] = pass_context(lambda ctx, v: fmt_date(v, ctx["lang"]))
    env.filters["month"] = pass_context(lambda ctx, v: fmt_date(v, ctx["lang"], full_ok=False))
    env.globals["brand"] = brand_icon
    env.globals["icon"] = lambda name: Markup(
        f'<svg class="icon icon-{name}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>')
    template = env.get_template("page.html")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    if STATIC.exists():
        shutil.copytree(STATIC, OUT, dirs_exist_ok=True)
    for asset in ("style.css", "main.js"):
        shutil.copy2(THEME / asset, OUT / asset)

    hints = set()
    written = []
    for lang in langs:
        root = "../" * prefix[lang].count("/")
        content = localize(raw, lang, langs)
        site = content.get("site") or {}
        person = content.get("person") or {}
        labels = {**LABELS, **(raw.get("labels") or {})}
        L = {k: localize(v, lang, langs) if isinstance(v, dict) else v for k, v in labels.items()}
        L = {k: v if isinstance(v, str) else str(v) for k, v in L.items()}

        name = person.get("name") or "First Last"
        initials = person.get("initials") or "".join(w[0] for w in name.split()[:2]).upper()
        photo = person.get("photo")
        if photo and not (STATIC / photo).is_file():
            hints.add(f"photo 'static/{photo}' not found: showing initials instead")
            photo = None
        logos = []
        for logo in person.get("logos") or []:
            if (STATIC / str(logo.get("file", ""))).is_file():
                logos.append(logo)
            else:
                hints.add(f"logo 'static/{logo.get('file')}' not found: not shown")
        links = [l for l in content.get("links") or [] if isinstance(l, dict) and l.get("url")]
        def named_list(value):
            value = [value] if isinstance(value, dict) else (value or [])
            return [a for a in value if isinstance(a, dict) and a.get("name")]

        affiliations = named_list(person.get("affiliation"))
        teams = named_list(person.get("team"))

        accent = site.get("accent") or "#9b1c31"
        description = site.get("description") or f"{name} — {plain(person.get('position', ''))}"
        base_url = (site.get("base_url") or "").rstrip("/")

        sections = build_sections(content, site, lang, L, root)
        if not sections:
            raise BuildError("No section to display: check site.sections in content.yml.")
        multipage = bool(site.get("multipage"))
        files = {s.id: f"{s.id}.html" if multipage and i else "index.html"
                 for i, s in enumerate(sections)}
        (OUT / prefix[lang]).mkdir(parents=True, exist_ok=True)

        for page in sections if multipage else sections[:1]:
            file = files[page.id]
            html_out = template.render(
                lang=lang, langs=langs, root=root, site=site, person=person, name=name,
                initials=initials, photo=photo, logos=logos, links=links, affiliations=affiliations, teams=teams,
                sections=sections, files=files, page=page, s=page, is_home=(file == "index.html"),
                one_page=not multipage,
                lang_links={l: root + prefix[l] + file for l in langs},
                alternates={l: f"{base_url}/{prefix[l]}{'' if file == 'index.html' else file}"
                            for l in langs} if base_url else {},
                L=L, description=plain(description), base_url=base_url,
                accent=accent, accent_dark=site.get("accent_dark") or "#f2879b",
                version=version,
                custom_css=(STATIC / "custom.css").is_file(),
                updated=fmt_date(today, lang), footer=site.get("footer"),
            )
            (OUT / prefix[lang] / file).write_text(html_out, encoding="utf-8")
            written.append(prefix[lang] + file)

    site_cfg = raw.get("site") or {}
    base = (site_cfg.get("base_url") or "").rstrip("/")
    if base:
        urls = "".join(
            f"  <url><loc>{html.escape(base)}/{'' if f.endswith('index.html') and '/' not in f else f}</loc>"
            f"<lastmod>{today.isoformat()}</lastmod></url>\n" for f in written)
        (OUT / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
            encoding="utf-8")
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
        written += ["sitemap.xml", "robots.txt"]
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    if not quiet:
        for h in sorted(hints):
            print(f"  · {h}")
        print(f"✓ Site built in {OUT.relative_to(ROOT)}/: {', '.join(written)}")


def _snapshot() -> dict:
    files = [CONTENT, Path(__file__).resolve(), *THEME.rglob("*"), *(STATIC.rglob("*") if STATIC.exists() else [])]
    return {str(f): f.stat().st_mtime for f in files if f.is_file()}


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve(port: int) -> None:
    build()

    def watch():
        last = _snapshot()
        while True:
            time.sleep(0.7)
            current = _snapshot()
            if current != last:
                last = current
                res = subprocess.run([sys.executable, str(Path(__file__).resolve())],
                                     capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"↻ {time.strftime('%H:%M:%S')} rebuilt — reload the page")
                else:
                    print(res.stderr.strip() or res.stdout.strip(), file=sys.stderr)

    threading.Thread(target=watch, daemon=True).start()
    handler = partial(_QuietHandler, directory=str(OUT))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"→ http://localhost:{port}/   (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the personal website into public/.")
    parser.add_argument("command", nargs="?", choices=["build", "serve"], default="build")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        serve(args.port) if args.command == "serve" else build()
    except BuildError as exc:
        sys.exit(f"✗ {exc}")


if __name__ == "__main__":
    main()
