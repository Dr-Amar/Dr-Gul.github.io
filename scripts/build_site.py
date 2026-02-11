from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

# Inputs
PROJECTS_YML = ROOT / "_data" / "projects.yml"
PUBS_BIB = ROOT / "data" / "publications.bib"

# Pages to update
PROJECTS_MD = ROOT / "_pages" / "projects.md"
PUBS_MD = ROOT / "_pages" / "publications.md"

# Markers in pages
START_P = "<!-- AUTO-GENERATED:PROJECTS:START -->"
END_P   = "<!-- AUTO-GENERATED:PROJECTS:END -->"
START_U = "<!-- AUTO-GENERATED:PUBLICATIONS:START -->"
END_U   = "<!-- AUTO-GENERATED:PUBLICATIONS:END -->"

# First-author detection (BibTeX format)
FIRST_AUTHOR_TOKEN = "Gul,"

def replace_block(text: str, start: str, end: str, new_block: str) -> str:
    """
    Replace everything between start/end markers (inclusive) with new_block.
    If markers do not exist, append them at the end.
    """
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    repl = f"{start}\n{new_block}\n{end}"

    if not pattern.search(text):
        return text.rstrip() + "\n\n" + repl + "\n"
    return pattern.sub(repl, text)

# ---------------------------
# PROJECTS
# ---------------------------

def render_projects() -> str:
    """
    Render projects from _data/projects.yml into Markdown sections.
    """
    if not PROJECTS_YML.exists():
        return "_No projects.yml found yet._\n"

    data = yaml.safe_load(PROJECTS_YML.read_text(encoding="utf-8"))
    lines = []

    for p in data.get("projects", []):
        name = p.get("name", "").strip()
        url = p.get("url", "").strip()
        summary = (p.get("summary", "") or "").strip()

        if name and url:
            lines.append(f"## [{name}]({url})")
        elif name:
            lines.append(f"## {name}")

        if summary:
            lines.append(summary)

        if p.get("highlights"):
            lines.append("")
            for h in p["highlights"]:
                lines.append(f"- {h}")

        if p.get("tags"):
            lines.append("")
            lines.append(f"**Tags:** {', '.join(p['tags'])}")

        lines.append("\n---\n")

    return "\n".join(lines).strip() + "\n"

# ---------------------------
# PUBLICATIONS
# ---------------------------

def _get_field(entry: str, field: str) -> str:
    """
    Extracts a BibTeX field value, handling:
      field = {...},
      field = "...",
      field = 2025,
    Works across multiline braced/quoted values.
    """
    pat = re.compile(
        rf"\b{re.escape(field)}\s*=\s*(\{{(?:.|\n)*?\}}|\"(?:.|\n)*?\"|[^,\n]+)",
        re.IGNORECASE
    )
    m = pat.search(entry)
    if not m:
        return ""

    v = m.group(1).strip()

    # strip braces/quotes
    if v.startswith("{") and v.endswith("}"):
        v = v[1:-1].strip()
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1].strip()

    # normalize whitespace
    return " ".join(v.split())

def parse_bibtex_entries(bib: str):
    """
    Parse BibTeX and return list of dicts:
      year, title, journal, doi, note, author, first_author
    """
    entries = []
    chunks = re.split(r"@\w+\s*{", bib)

    for ch in chunks[1:]:
        title = _get_field(ch, "title")
        if not title:
            continue

        year = _get_field(ch, "year")
        journal = _get_field(ch, "journal")
        doi = _get_field(ch, "doi")
        note = _get_field(ch, "note")
        author = _get_field(ch, "author")

        # First-author if author exists and starts with "Gul,"
        is_first = bool(author) and author.strip().startswith(FIRST_AUTHOR_TOKEN)

        entries.append({
            "year": year,
            "title": title,
            "journal": journal,
            "doi": doi,
            "note": note,
            "author": author,
            "first_author": is_first,
        })

    # Sort by year desc (missing years go last)
    def sort_key(x):
        y = x.get("year", "")
        return (y if y.isdigit() else "0000", x.get("title", ""))

    entries.sort(key=sort_key, reverse=True)
    return entries

def render_publications() -> str:
    """
    Render publications from data/publications.bib into Markdown list.
    DOI button only (no PDFs).
    """
    if not PUBS_BIB.exists():
        return "_No BibTeX file found yet._\n"

    bib = PUBS_BIB.read_text(encoding="utf-8", errors="ignore")
    pubs = parse_bibtex_entries(bib)

    lines = []
    for p in pubs:
        y = f" ({p['year']})" if p.get("year") else ""
        j = f"*{p['journal']}*" if p.get("journal") else ""
        n = f" — {p['note']}" if p.get("note") else ""

        # labels
        labels = []
        if p.get("first_author"):
            labels.append("**First-author**")
        label_str = f" · {' | '.join(labels)}" if labels else ""

        # DOI button-like link (Markdown)
        doi_btn = f" [DOI](https://doi.org/{p['doi']})" if p.get("doi") else ""

        if j:
            lines.append(f"- **{p['title']}** — {j}{y}{n}{label_str}{doi_btn}")
        else:
            lines.append(f"- **{p['title']}**{y}{n}{label_str}{doi_btn}")

    return "\n".join(lines).strip() + "\n"

# ---------------------------
# MAIN
# ---------------------------

def main():
    # Update Projects page
    if PROJECTS_MD.exists():
        p_text = PROJECTS_MD.read_text(encoding="utf-8")
        p_block = render_projects()
        PROJECTS_MD.write_text(
            replace_block(p_text, START_P, END_P, p_block),
            encoding="utf-8",
            newline="\n"
        )

    # Update Publications page
    if PUBS_MD.exists():
        u_text = PUBS_MD.read_text(encoding="utf-8")
        u_block = render_publications()
        PUBS_MD.write_text(
            replace_block(u_text, START_U, END_U, u_block),
            encoding="utf-8",
            newline="\n"
        )

if __name__ == "__main__":
    main()
