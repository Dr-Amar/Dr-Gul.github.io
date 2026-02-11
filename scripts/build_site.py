from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

# Canonical locations (recommended)
PROJECTS_YML = ROOT / "_data" / "projects.yml"
PUBS_BIB = ROOT / "data" / "publications.bib"

PROJECTS_MD = ROOT / "_pages" / "projects.md"
PUBS_MD = ROOT / "_pages" / "publications.md"

START_P = "<!-- AUTO-GENERATED:PROJECTS:START -->"
END_P   = "<!-- AUTO-GENERATED:PROJECTS:END -->"
START_U = "<!-- AUTO-GENERATED:PUBLICATIONS:START -->"
END_U   = "<!-- AUTO-GENERATED:PUBLICATIONS:END -->"

# Your name variants for "first-author" detection
FIRST_AUTHOR_PATTERNS = [
    r"^Gul,\s*M\.?\s*A\.?,",                 # Gul, M.A.,
    r"^Gul,\s*Muhammad\s+Amar\s*,",          # Gul, Muhammad Amar,
    r"^Gul,\s*Muhammad\s+Amar\s+Gul\s*,",    # Gul, Muhammad Amar Gul,
]

DOI_REGEX = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)", re.IGNORECASE)
DOI_URL_REGEX = re.compile(r"doi\.org/(10\.\d{4,9}/[^\s\"<>]+)", re.IGNORECASE)

def replace_block(text: str, start: str, end: str, new_block: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    repl = f"{start}\n{new_block}\n{end}"
    if not pattern.search(text):
        return text.rstrip() + "\n\n" + repl + "\n"
    return pattern.sub(repl, text)

def render_projects() -> str:
    if not PROJECTS_YML.exists():
        return "_No projects file found yet._\n"

    data = yaml.safe_load(PROJECTS_YML.read_text(encoding="utf-8"))
    lines = []
    for p in data.get("projects", []):
        name = str(p.get("name", "")).strip()
        url = str(p.get("url", "")).strip()
        summary = str(p.get("summary", "")).strip()

        if name and url:
            lines.append(f"## [{name}]({url})")
        elif name:
            lines.append(f"## {name}")

        if summary:
            lines.append(summary)

        highlights = p.get("highlights") or []
        if highlights:
            lines.append("")
            for h in highlights:
                lines.append(f"- {str(h).strip()}")

        tags = p.get("tags") or []
        if tags:
            lines.append("")
            lines.append(f"**Tags:** {', '.join([str(t).strip() for t in tags])}")

        lines.append("\n---\n")

    return "\n".join(lines).strip() + "\n"

def _clean_val(s: str) -> str:
    return " ".join(s.replace("\n", " ").split()).strip()

def _field(ch: str, key: str) -> str:
    # Handles: key = {..} OR key = "..."  (best-effort)
    m = re.search(rf"\b{re.escape(key)}\s*=\s*(\{{.*?\}}|\".*?\")\s*,", ch, re.I | re.S)
    if not m:
        return ""
    v = m.group(1).strip()
    if v.startswith("{") and v.endswith("}"):
        v = v[1:-1]
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1]
    return _clean_val(v)

def _year(ch: str) -> str:
    m = re.search(r"\byear\s*=\s*[{(\"]?(\d{4})", ch, re.I)
    return m.group(1) if m else ""

def _is_first_author(author_field: str) -> bool:
    a = (author_field or "").strip()
    for pat in FIRST_AUTHOR_PATTERNS:
        if re.search(pat, a, flags=re.I):
            return True
    return False

def _extract_doi(*texts: str) -> str:
    """
    Return DOI string if found in any text, else "".
    Accepts:
      - doi = {10....}
      - url = {https://doi.org/10....}
      - note/text containing 'DOI:10....'
    """
    for t in texts:
        if not t:
            continue
        t = t.strip()

        m = DOI_URL_REGEX.search(t)
        if m:
            return m.group(1).rstrip(").,;]}>")

        m = DOI_REGEX.search(t)
        if m:
            return m.group(1).rstrip(").,;]}>")

    return ""

def parse_bibtex_entries(bib: str):
    entries = []
    chunks = re.split(r"@\w+\s*{", bib)

    for ch in chunks[1:]:
        title = _field(ch, "title")
        if not title:
            continue

        author = _field(ch, "author")
        journal = _field(ch, "journal")
        year = _year(ch)

        doi_field = _field(ch, "doi")
        url_field = _field(ch, "url")
        note_field = _field(ch, "note")

        # If doi is missing, try extracting from url/note/title (or any pasted doi.org)
        doi = doi_field or _extract_doi(url_field, note_field, title)

        entries.append({
            "year": year,
            "title": title,
            "author": author,
            "journal": journal,
            "doi": doi,
            "url": url_field,
            "note": note_field,
            "first_author": _is_first_author(author),
        })

    # Sort by year desc, then first-author first
    def keyfn(x):
        y = int(x["year"]) if (x.get("year") or "").isdigit() else -1
        fa = 1 if x.get("first_author") else 0
        return (y, fa)

    entries.sort(key=keyfn, reverse=True)
    return entries

def render_publications() -> str:
    if not PUBS_BIB.exists():
        return "_No BibTeX file found yet. Expected: `data/publications.bib`._\n"

    bib = PUBS_BIB.read_text(encoding="utf-8", errors="ignore")
    pubs = parse_bibtex_entries(bib)

    if not pubs:
        return "_No publications parsed from BibTeX._\n"

    lines = []
    current_year = None

    for p in pubs:
        year = p.get("year", "Unknown")

        # 🔹 YEAR HEADER
        if year != current_year:
            lines.append(f"\n## {year}\n")
            current_year = year

        journal = p.get("journal", "")
        doi = p.get("doi", "")
        note = p.get("note", "")
        first_author = p.get("first_author", False)

        badges = []
        if first_author:
            badges.append("**[First-author]**")
        if note:
            badges.append(f"*{note}*")

        badge_str = (" " + " · ".join(badges)) if badges else ""

        parts = [f"**{p['title']}**"]
        if journal:
            parts.append(f"*{journal}*")

        line = " — ".join(parts) + badge_str

        # 🔹 DOI BUTTON (ALL PAPERS WITH DOI)
        if doi:
            doi_url = f"https://doi.org/{doi}"
            line += f' &nbsp; <a class="doi-btn" href="{doi_url}" target="_blank" rel="noopener">DOI</a>'

        lines.append(f"- {line}")

    lines.append("\n> Tip: You can style the DOI button via CSS class `.doi-btn`.")

    return "\n".join(lines).strip() + "\n"


def main():
    # Projects page
    p_text = PROJECTS_MD.read_text(encoding="utf-8") if PROJECTS_MD.exists() else ""
    p_block = render_projects()
    PROJECTS_MD.write_text(
        replace_block(p_text, START_P, END_P, p_block),
        encoding="utf-8",
        newline="\n",
    )

    # Publications page
    u_text = PUBS_MD.read_text(encoding="utf-8") if PUBS_MD.exists() else ""
    u_block = render_publications()
    PUBS_MD.write_text(
        replace_block(u_text, START_U, END_U, u_block),
        encoding="utf-8",
        newline="\n",
    )

if __name__ == "__main__":
    main()
