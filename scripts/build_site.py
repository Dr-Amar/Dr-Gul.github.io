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
    r"^Gul,\s*M\.?A\.?,",                 # Gul, M.A.,
    r"^Gul,\s*Muhammad\s+Amar\s*,",       # Gul, Muhammad Amar,
    r"^Gul,\s*Muhammad\s+Amar\s+Gul\s*,", # Gul, Muhammad Amar Gul,
]

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
        name = p.get("name", "").strip()
        url = p.get("url", "").strip()
        summary = p.get("summary", "").strip()

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
    a = author_field.strip()
    for pat in FIRST_AUTHOR_PATTERNS:
        if re.search(pat, a, flags=re.I):
            return True
    return False

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
        doi = _field(ch, "doi")
        note = _field(ch, "note")

        entries.append({
            "year": year,
            "title": title,
            "author": author,
            "journal": journal,
            "doi": doi,
            "note": note,
            "first_author": _is_first_author(author),
        })

    # Sort by year desc, then first-author first
    def keyfn(x):
        y = int(x["year"]) if x["year"].isdigit() else -1
        fa = 1 if x["first_author"] else 0
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
    for p in pubs:
        year = p.get("year", "")
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

        parts = []
        parts.append(f"**{p['title']}**")
        if journal:
            parts.append(f"*{journal}*")
        if year:
            parts.append(f"({year})")

        line = " — ".join(parts) + badge_str

        if doi:
            doi_url = f"https://doi.org/{doi}"
            # Button-like link (works with your site CSS if you add .doi-btn style)
            line += f' &nbsp; <a class="doi-btn" href="{doi_url}" target="_blank" rel="noopener">DOI</a>'

        lines.append(f"- {line}")

    # Add tiny CSS hint block (optional)
    lines.append("")
    lines.append("> Tip: You can style the DOI button via CSS class `.doi-btn`.")

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
