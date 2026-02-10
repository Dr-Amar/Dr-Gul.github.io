from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_YML = ROOT / "_data" / "projects.yml"
PUBS_BIB = ROOT / "data" / "publications.bib"
PROJECTS_MD = ROOT / "_pages" / "projects.md"
PUBS_MD = ROOT / "_pages" / "publications.md"

START_P = "<!-- AUTO-GENERATED:PROJECTS:START -->"
END_P   = "<!-- AUTO-GENERATED:PROJECTS:END -->"
START_U = "<!-- AUTO-GENERATED:PUBLICATIONS:START -->"
END_U   = "<!-- AUTO-GENERATED:PUBLICATIONS:END -->"

def replace_block(text: str, start: str, end: str, new_block: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    repl = f"{start}\n{new_block}\n{end}"
    if not pattern.search(text):
        return text.rstrip() + "\n\n" + repl + "\n"
    return pattern.sub(repl, text)

def render_projects() -> str:
    data = yaml.safe_load(PROJECTS_YML.read_text(encoding="utf-8"))
    lines = []
    for p in data.get("projects", []):
        lines.append(f"## [{p['name']}]({p['url']})")
        lines.append(p.get("summary", "").strip())
        if p.get("highlights"):
            lines.append("")
            for h in p["highlights"]:
                lines.append(f"- {h}")
        if p.get("tags"):
            lines.append("")
            lines.append(f"**Tags:** {', '.join(p['tags'])}")
        lines.append("\n---\n")
    return "\n".join(lines).strip() + "\n"

def parse_bibtex_entries(bib: str):
    entries = []
    chunks = re.split(r"@\w+\s*{", bib)
    for ch in chunks[1:]:
        year = re.search(r"\byear\s*=\s*[{(\"]?(\d{4})", ch, re.I)
        title = re.search(r"\btitle\s*=\s*[{(\"](.+?)[})\"]\s*,", ch, re.I | re.S)
        journal = re.search(r"\bjournal\s*=\s*[{(\"](.+?)[})\"]\s*,", ch, re.I | re.S)
        doi = re.search(r"\bdoi\s*=\s*[{(\"](.+?)[})\"]\s*,", ch, re.I | re.S)
        if not title:
            continue
        entries.append({
            "year": year.group(1) if year else "",
            "title": " ".join(title.group(1).split()),
            "journal": " ".join(journal.group(1).split()) if journal else "",
            "doi": " ".join(doi.group(1).split()) if doi else "",
        })
    entries.sort(key=lambda x: x.get("year",""), reverse=True)
    return entries

def render_publications() -> str:
    if not PUBS_BIB.exists():
        return "_No BibTeX file found yet._\n"
    bib = PUBS_BIB.read_text(encoding="utf-8", errors="ignore")
    pubs = parse_bibtex_entries(bib)
    lines = []
    for p in pubs:
        y = f" ({p['year']})" if p.get("year") else ""
        j = f" — *{p['journal']}*" if p.get("journal") else ""
        d = f" · https://doi.org/{p['doi']}" if p.get("doi") else ""
        lines.append(f"- **{p['title']}**{j}{y}{d}")
    return "\n".join(lines).strip() + "\n"

def main():
    # Projects
    p_text = PROJECTS_MD.read_text(encoding="utf-8")
    p_block = render_projects()
    PROJECTS_MD.write_text(replace_block(p_text, START_P, END_P, p_block), encoding="utf-8", newline="\n")

    # Publications
    u_text = PUBS_MD.read_text(encoding="utf-8")
    u_block = render_publications()
    PUBS_MD.write_text(replace_block(u_text, START_U, END_U, u_block), encoding="utf-8", newline="\n")

if __name__ == "__main__":
    main()

