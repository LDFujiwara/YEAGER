"""
Reads every data/*.json file (one per day, written by run_pipeline.py) and
builds a single combined docs/data.json plus the static site files that
read it. GitHub Pages serves everything in docs/ directly. Also renders
assessments/*.md files into their own pages (see build_assessments()).

The actual HTML/CSS/JS live as separate files under scripts/templates/
rather than embedded as string literals here, to keep this file short
and each template independently editable.
"""
import glob
import json
import os
import re

import markdown as md_lib

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
ASSESSMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "assessments")
ASSESSMENTS_OUT_DIR = os.path.join(DOCS_DIR, "assessments")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _read_template(name):
    with open(os.path.join(TEMPLATES_DIR, name)) as f:
        return f.read()


def _escape_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_all_clusters():
    combined = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json")), reverse=True):
        day = os.path.basename(path).replace(".json", "")
        with open(path) as f:
            clusters = json.load(f)
        for cluster in clusters:
            cluster["date"] = day
            combined.append(cluster)
    return combined


def write_data_json(clusters):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "data.json"), "w") as f:
        json.dump(clusters, f, indent=2)


def write_static_files():
    """Writes index.html/style.css/app.js if they don't already exist.
    These are static and don't need regenerating every run — only
    docs/data.json changes day to day."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    for name in ("index.html", "style.css", "app.js"):
        out_path = os.path.join(DOCS_DIR, name)
        if not os.path.exists(out_path):
            with open(out_path, "w") as f:
                f.write(_read_template(name))


def build_assessments():
    """Renders each assessments/*.md file into its own page under
    docs/assessments/, and writes docs/assessments-index.json listing
    them all for the site's Assessments tab.

    Filename convention: YYYY-MM-DD-short-title.md. The file's first
    line should be a single '# Title' heading; everything after that
    is the assessment body, written in plain markdown.
    """
    os.makedirs(ASSESSMENTS_OUT_DIR, exist_ok=True)
    index = []
    page_template = _read_template("assessment_page.html")

    if os.path.isdir(ASSESSMENTS_DIR):
        for fname in sorted(os.listdir(ASSESSMENTS_DIR), reverse=True):
            match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", fname)
            if not match:
                continue  # skip README.md and anything not matching the naming convention
            date, slug = match.group(1), match.group(2)

            with open(os.path.join(ASSESSMENTS_DIR, fname)) as f:
                content = f.read()
            lines = content.splitlines()
            title = slug.replace("-", " ").title()
            body_lines = lines
            if lines and lines[0].startswith("# "):
                title = lines[0][2:].strip()
                body_lines = lines[1:]
            body_html = md_lib.markdown("\n".join(body_lines), extensions=["extra"])

            page_html = page_template.format(
                title=_escape_html(title), date=date, body=body_html
            )
            with open(os.path.join(ASSESSMENTS_OUT_DIR, f"{slug}.html"), "w") as f:
                f.write(page_html)

            index.append({"title": title, "date": date, "slug": slug})

    with open(os.path.join(DOCS_DIR, "assessments-index.json"), "w") as f:
        json.dump(index, f, indent=2)
    return index


def main():
    clusters = load_all_clusters()
    write_data_json(clusters)
    write_static_files()
    assessments = build_assessments()
    print(f"Built site with {len(clusters)} clusters and {len(assessments)} assessments into docs/")


if __name__ == "__main__":
    main()
