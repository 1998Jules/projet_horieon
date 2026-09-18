"""Génère docs/Documentation_E-commune.pdf (et docs/index.html) à partir de README.md et DOCUMENTATION.md.

Le Markdown est converti en une page HTML mise en forme (page de garde,
sommaire, pages A4 blanches, diagrammes Mermaid), puis imprimée en PDF par
Chrome ou Edge en mode sans interface.

Prérequis (hors requirements.txt, uniquement pour la documentation) :
    pip install markdown pymdown-extensions
    + Google Chrome ou Microsoft Edge (variable CHROME_PATH pour un autre chemin)
    + une connexion internet (polices et bibliothèque Mermaid)

Usage, depuis la racine du projet :
    python docs/generer_pdf.py
"""
import html
import os
import re
import subprocess
import sys
import tempfile

import markdown

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "Documentation_E-commune.pdf")
CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
CHROME = next((c for c in CHROME_CANDIDATES if c and os.path.exists(c)), None)
if CHROME is None:
    sys.exit("Chrome ou Edge introuvable : définissez la variable CHROME_PATH.")

FILE_IDS = {"README.md": "doc0", "DOCUMENTATION.md": "doc1"}


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


# Chapitres : le README, puis chaque « # Partie N : … » de DOCUMENTATION.md (le
# préambule et le sommaire du fichier sont remplacés par la page de garde et le
# sommaire du PDF). Les parties partagent le même préfixe d'ancres (doc1).
DOCS = [(read("README.md"), "doc0", "Présentation")]
for n, part in enumerate(re.split(r"(?m)^(?=# Partie \d)", read("DOCUMENTATION.md"))[1:], start=1):
    DOCS.append((re.sub(r"\n---\s*$", "\n", part), "doc1", f"Partie {n}"))


def slugify(value, separator="-"):
    """Même règle que GitHub : minuscules, ponctuation retirée, espaces -> tirets."""
    value = re.sub(r"<[^>]+>", "", value).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value)
    return value.replace(" ", separator)


def mermaid_fence(source, language, css_class, options, md, **kwargs):
    return f'<div class="mermaid">{html.escape(source)}</div>'


def convert(text, doc_id):
    # <details> : toujours ouvert à l'impression, et Markdown interprété à l'intérieur
    text = text.replace("<details>", '<details open markdown="1">')
    md = markdown.Markdown(tab_length=2, extensions=[
        "tables", "md_in_html", "sane_lists",
        "toc",
        "pymdownx.superfences", "pymdownx.tasklist",
    ], extension_configs={
        "toc": {"slugify": slugify, "permalink": False},
        "pymdownx.superfences": {"custom_fences": [
            {"name": "mermaid", "class": "mermaid", "format": mermaid_fence}]},
    })
    body = md.convert(text)
    # Ancres propres à chaque document
    body = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{doc_id}-{m.group(1)}"', body)

    def fix_link(m):
        href = m.group(1)
        if href.startswith("#"):
            return f'href="#{doc_id}-{href[1:]}"'
        target = re.match(r"(?:\.\./|docs/)?([\w\-]+\.md)(#.*)?$", href)
        if target and target.group(1) in FILE_IDS:
            other = FILE_IDS[target.group(1)]
            return f'href="#{other}-{target.group(2)[1:]}"' if target.group(2) else f'href="#{other}"'
        return m.group(0)

    body = re.sub(r'href="([^"]+)"', fix_link, body)
    return body


def toc_entries(body, doc_id):
    """(niveau, id, texte) des titres h1/h2 d'un document converti."""
    out = []
    for level, hid, inner in re.findall(r'<h([12]) id="([^"]+)">(.*?)</h\1>', body, flags=re.S):
        out.append((int(level), hid, re.sub(r"<[^>]+>", "", inner)))
    return out


chapters, toc = [], []
for text, doc_id, label in DOCS:
    body = convert(text, doc_id)
    entries = toc_entries(body, doc_id)
    first_id, title = (entries[0][1], entries[0][2]) if entries else (doc_id, label)
    title = re.sub(r"^Partie \d+ : ", "", title)
    toc.append((first_id, label, title, [e for e in entries if e[0] == 2 and "sommaire" not in e[1]]))
    chapter_label = f'<div class="chapter-label">{label}</div>' if doc_id == "doc0" else ""
    # id du chapitre : doc0 / doc1 pour les liens vers un fichier sans ancre (1re partie)
    section_id = doc_id if label in ("Présentation", "Partie 1") else first_id + "-chapitre"
    chapters.append(f"""
<section class="chapter" id="{section_id}">
  {chapter_label}
  {body}
</section>""")

toc_html = "".join(
    f'<li><a href="#{first_id}"><span class="toc-label">{label}</span>{html.escape(title)}</a>'
    + ("<ol>" + "".join(f'<li><a href="#{hid}">{html.escape(t)}</a></li>' for _, hid, t in subs) + "</ol>" if subs else "")
    + "</li>"
    for first_id, label, title, subs in toc
)

CSS = r"""
@page { size: A4; margin: 20mm 18mm 22mm 18mm;
  @bottom-left { content: "E-commune · Documentation"; font: 8pt Inter, 'Segoe UI', sans-serif; color: #7a8a80; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt Inter, 'Segoe UI', sans-serif; color: #7a8a80; }
}
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
:root { --green: #0f5132; --green-2: #15803d; --green-soft: #ecf6ef; --line: #d8e2dc; --ink: #1c2420; --muted: #5b6b62;
        --amber-soft: #fff8e6; --amber: #b7791f; }
* { box-sizing: border-box; }
html { background: #fff; }
body { margin: 0; color: var(--ink); background: #fff; font: 10.2pt/1.55 Inter, 'Segoe UI', Roboto, sans-serif;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }

/* Page de garde */
.cover { height: 297mm; display: flex; flex-direction: column; justify-content: space-between;
         padding: 30mm 22mm 24mm; background: linear-gradient(160deg, #0f5132 0%, #146c43 55%, #1f8a55 100%); color: #fff;
         break-after: page; }
.cover .kicker { font-size: 10pt; letter-spacing: .18em; text-transform: uppercase; opacity: .8; }
.cover h1 { font-size: 34pt; line-height: 1.1; margin: 10mm 0 4mm; font-weight: 800; border: 0; color: #fff; }
.cover .subtitle { font-size: 14pt; opacity: .92; max-width: 140mm; }
.cover .meta { display: grid; grid-template-columns: auto 1fr; gap: 2mm 8mm; font-size: 10pt; opacity: .95; }
.cover .meta b { font-weight: 600; opacity: .75; }
.cover .band { border-top: 1px solid rgba(255,255,255,.35); padding-top: 6mm; }

/* Sommaire */
.toc { break-after: page; }
.toc h1 { font-size: 22pt; color: var(--green); margin: 0 0 6mm; border: 0; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc > ol > li { margin: 0 0 3.2mm; padding: 3mm 4.5mm; background: var(--green-soft); border-radius: 3mm; break-inside: avoid; }
.toc > ol > li > a { font-weight: 700; font-size: 12pt; color: var(--green); text-decoration: none; display: block; }
.toc-label { display: inline-block; min-width: 32mm; font-size: 8pt; text-transform: uppercase; letter-spacing: .08em;
             color: var(--green-2); font-weight: 600; }
.toc ol ol { margin: 2mm 0 0 32mm; columns: 2; column-gap: 8mm; }
.toc ol ol li { font-size: 8.6pt; margin: .3mm 0; break-inside: avoid; }
.toc ol ol a { color: var(--ink); text-decoration: none; }

/* Chapitres */
.chapter { break-before: page; }
.chapter-label { font-size: 9pt; text-transform: uppercase; letter-spacing: .16em; color: var(--green-2); font-weight: 700; }
h1 { font-size: 22pt; line-height: 1.2; color: var(--green); margin: 1mm 0 6mm; padding-bottom: 3mm; border-bottom: 2.5px solid var(--green); }
h2 { font-size: 14.5pt; color: var(--green); margin: 9mm 0 3mm; padding-bottom: 1.5mm; border-bottom: 1px solid var(--line);
     break-after: avoid; }
h3 { font-size: 11.5pt; color: #1d3b2a; margin: 6mm 0 2mm; break-after: avoid; }
h4 { font-size: 10.5pt; margin: 4mm 0 1.5mm; break-after: avoid; }
p { margin: 0 0 2.6mm; }
a { color: var(--green-2); text-decoration: none; }
strong { color: #10251a; }
hr { border: 0; border-top: 1px solid var(--line); margin: 6mm 0; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin: .8mm 0; }
li > p { margin: 0; }

/* Encadrés (citations) */
blockquote { margin: 3mm 0 4mm; padding: 3mm 4mm; background: var(--green-soft); border-left: 3.5px solid var(--green-2);
             border-radius: 0 2mm 2mm 0; break-inside: avoid; }
blockquote p:last-child { margin: 0; }
blockquote.warn { background: var(--amber-soft); border-left-color: var(--amber); }

/* Code */
code { font: 8.6pt 'JetBrains Mono', Consolas, monospace; background: #f1f4f2; padding: .3mm 1.2mm; border-radius: 1mm; color: #0b3d25; }
pre { background: #f6f8f7; border: 1px solid var(--line); border-left: 3px solid var(--green-2); border-radius: 2mm;
      padding: 3mm 4mm; margin: 2mm 0 4mm; white-space: pre-wrap; word-break: break-word; }
pre code { background: none; padding: 0; font-size: 8.3pt; line-height: 1.5; color: #1c2420; }
.highlight { margin: 0; }

/* Tableaux */
table { width: 100%; border-collapse: collapse; margin: 2mm 0 5mm; font-size: 8.9pt; line-height: 1.42; }
thead { display: table-header-group; }
th { background: var(--green); color: #fff; text-align: left; font-weight: 600; padding: 1.8mm 2.4mm; }
td { padding: 1.6mm 2.4mm; border-bottom: 1px solid var(--line); vertical-align: top; }
td code, th code { overflow-wrap: anywhere; }
tbody tr:nth-child(even) td { background: #f7faf8; }
tr { break-inside: avoid; }
td code, th code { font-size: 8pt; }

/* Listes de contrôle */
.task-list-item { list-style: none; margin-left: -5mm; }
.task-list-item input { margin-right: 2mm; }

/* Diagrammes */
.mermaid { margin: 3mm 0 5mm; padding: 4mm; border: 1px solid var(--line); border-radius: 2mm; background: #fbfdfc;
           text-align: center; break-inside: avoid; }
.mermaid svg { max-width: 100% !important; height: auto; }
.mermaid svg[aria-roledescription^="flowchart"] { width: 100% !important; max-height: 150mm; }

details { margin: 3mm 0; padding: 3mm 4mm; border: 1px dashed var(--line); border-radius: 2mm; }
summary { font-weight: 600; color: var(--green); margin-bottom: 2mm; }
"""

page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>E-commune — Documentation</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>
<div class="cover">
  <div>
    <div class="kicker">Documentation du projet</div>
    <h1>E-commune Horison</h1>
    <div class="subtitle">Géoportail et surveillance agricole de la commune de Blitta 2 (Togo)</div>
  </div>
  <div class="band">
    <div class="meta">
      <b>Commune</b><span>Blitta 2 — Agbandi, Langabou, Koffiti, Tcharè-Baou</span>
      <b>Préfecture</b><span>Blitta, région Centrale</span>
      <b>Contenu</b><span>Présentation · Comprendre · Installer et lancer · Architecture · Améliorer</span>
      <b>Dépôt</b><span>github.com/1998Jules/projet_horieon</span>
      <b>Édition</b><span>Septembre 2026</span>
    </div>
  </div>
</div>
<div class="toc"><h1>Sommaire</h1><ol>{toc_html}</ol></div>
{''.join(chapters)}
<script type="module">
  // Encadrés d'avertissement
  document.querySelectorAll('blockquote').forEach(b => {{ if (b.textContent.includes('⚠️')) b.classList.add('warn'); }});
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.3/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: false, theme: 'base', fontFamily: 'Inter, Segoe UI, sans-serif',
    themeVariables: {{ primaryColor: '#ecf6ef', primaryBorderColor: '#15803d', primaryTextColor: '#1c2420',
                       lineColor: '#5b6b62', secondaryColor: '#fff8e6', tertiaryColor: '#f7faf8', fontSize: '13px' }},
    flowchart: {{ htmlLabels: true, curve: 'basis' }} }});
  await document.fonts.ready;  // Mermaid mesure les textes : attendre les polices
  // Identifiants explicites : ceux de Mermaid dérivent de l'horloge, figée par Chrome
  // sans interface, et deux diagrammes identifiés pareil se mélangent.
  let n = 0;
  for (const el of document.querySelectorAll('.mermaid')) {{
    const {{ svg }} = await mermaid.render(`diagramme-${{++n}}`, el.textContent);
    el.innerHTML = svg;
    el.setAttribute('data-processed', 'true');
  }}
</script>
</body></html>"""

# Version web (docs/index.html, publiable avec GitHub Pages) : mêmes contenus,
# présentés comme des feuilles A4 blanches sur fond gris, avec un lien vers le PDF.
SCREEN_CSS = r"""
@media screen {
  html, body { background: #e6e9e7; }
  .topbar { position: sticky; top: 0; z-index: 10; display: flex; justify-content: space-between; align-items: center;
            gap: 12px; padding: 10px 16px; background: #0f5132; color: #fff; font-size: 14px; }
  .topbar a { color: #fff; font-weight: 600; background: rgba(255,255,255,.15); padding: 6px 12px; border-radius: 6px; }
  .cover, .toc, .chapter { width: min(210mm, calc(100% - 32px)); margin: 24px auto;
                           box-shadow: 0 1px 3px rgba(0,0,0,.12), 0 8px 24px rgba(0,0,0,.08); border-radius: 2px; }
  .toc, .chapter { background: #fff; }
  .cover { height: auto; min-height: min(200mm, 80vh); gap: 24px; }
  .toc, .chapter { padding: 20mm 18mm 22mm; }
}
@media screen and (max-width: 700px) {
  table { display: block; overflow-x: auto; }
  .toc, .chapter { padding: 20px 16px; }
  .cover { padding: 40px 20px; }
  .cover h1 { font-size: 26pt; }
  .toc ol ol { margin-left: 0; columns: 1; }
}
@media print { .topbar { display: none; } }
"""
def file_url(path):
    return "file:///" + path.replace("\\", "/")


def render_diagrams(source_html):
    """Fait dessiner les diagrammes par Chrome et renvoie la page figée (sans script).

    Imprimer directement la page avec son script donne parfois un diagramme vide
    (impression lancée avant la fin du dessin) : on fige donc le résultat d'abord.
    """
    src = os.path.join(tempfile.gettempdir(), "documentation_e-commune_source.html")
    with open(src, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(source_html)
    expected = source_html.count('<div class="mermaid">')
    for attempt in range(1, 4):
        dom = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=30000",
             "--window-size=1280,1600", "--dump-dom", file_url(src)],
            check=True, capture_output=True).stdout.decode("utf-8").replace("\r\n", "\n")
        svgs = re.findall(r'<div class="mermaid"[^>]*>(<svg[\s\S]*?</svg>)', dom)
        drawn = [s for s in svgs if s.count("<g") > 3]
        if len(drawn) == expected:
            dom = re.sub(r'<script type="module">[\s\S]*?</script>', "", dom)
            return "<!doctype html>\n" + dom
        print(f"  diagrammes dessinés : {len(drawn)}/{expected} (essai {attempt}), nouvel essai…")
    sys.exit("Les diagrammes Mermaid n'ont pas pu être dessinés (connexion internet ?).")


static_page = render_diagrams(page)

web_page = static_page.replace(
    '<meta charset="utf-8">',
    '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">', 1,
).replace("</style>", SCREEN_CSS + "</style>", 1).replace(
    "<body>",
    '<body>\n<div class="topbar"><span>E-commune · Documentation</span>'
    '<a href="Documentation_E-commune.pdf">Télécharger le PDF</a></div>', 1)
with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(web_page)
print("Web  :", os.path.join(ROOT, "docs", "index.html"))

html_path = os.path.join(tempfile.gettempdir(), "documentation_e-commune.html")
with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(static_page)

subprocess.run([
    CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
    "--virtual-time-budget=30000", "--run-all-compositor-stages-before-draw",
    f"--print-to-pdf={OUT_PDF}", "file:///" + html_path.replace("\\", "/"),
], check=True, capture_output=True)
print("PDF  :", OUT_PDF, os.path.getsize(OUT_PDF) // 1024, "Ko")
