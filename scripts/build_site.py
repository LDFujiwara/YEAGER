"""
Reads every data/*.json file (one per day, written by run_pipeline.py) and
builds a single combined docs/data.json plus the static site files that
read it. GitHub Pages serves everything in docs/ directly — no build
step needed at view time, all filtering happens client-side in the browser.
"""
import glob
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


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
    index_path = os.path.join(DOCS_DIR, "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write(INDEX_HTML)
    style_path = os.path.join(DOCS_DIR, "style.css")
    if not os.path.exists(style_path):
        with open(style_path, "w") as f:
            f.write(STYLE_CSS)
    app_path = os.path.join(DOCS_DIR, "app.js")
    if not os.path.exists(app_path):
        with open(app_path, "w") as f:
            f.write(APP_JS)


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Intel News Board</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>Intel News Board</h1>
    <div class="filters">
      <select id="domainFilter"><option value="">All Domains</option></select>
      <select id="functionFilter"><option value="">All Joint Functions</option></select>
      <select id="typeFilter"><option value="">All Types</option></select>
      <input id="searchBox" type="text" placeholder="Search...">
    </div>
  </header>
  <main id="cardList"></main>
  <script src="app.js"></script>
</body>
</html>
"""

STYLE_CSS = """* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
body { background: #14161c; color: #d7dae0; }
header { position: sticky; top: 0; background: #1a1d24; padding: 16px 20px; border-bottom: 1px solid #2a2e38; z-index: 10; }
header h1 { font-size: 18px; margin-bottom: 10px; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; }
.filters select, .filters input { background: #20232c; color: #d7dae0; border: 1px solid #2a2e38; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
.filters input { flex: 1; min-width: 200px; }
main { padding: 20px; max-width: 900px; margin: 0 auto; }
.card { background: #1a1d24; border: 1px solid #2a2e38; border-radius: 8px; padding: 16px; margin-bottom: 14px; }
.card-date { font-size: 11px; color: #7d8494; margin-bottom: 6px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #2b6cb0; color: white; }
.tag.function { background: #6b46c1; }
.tag.type { background: #b7791f; }
.highlight { font-size: 14px; margin-bottom: 6px; padding-left: 14px; border-left: 2px solid #2a2e38; }
.highlight a { color: #5b9bd5; text-decoration: none; font-size: 12px; margin-left: 6px; }
.sources { font-size: 12px; color: #7d8494; margin-top: 8px; }
"""

APP_JS = """let allClusters = [];

async function load() {
  const res = await fetch('data.json');
  allClusters = await res.json();
  populateFilters();
  render();
}

function populateFilters() {
  const domains = new Set(), functions = new Set(), types = new Set();
  allClusters.forEach(c => {
    (c.tags.domains || []).forEach(d => domains.add(d));
    (c.tags.joint_functions || []).forEach(f => functions.add(f));
    if (c.tags.type) types.add(c.tags.type);
  });
  fillSelect('domainFilter', domains);
  fillSelect('functionFilter', functions);
  fillSelect('typeFilter', types);
}

function fillSelect(id, values) {
  const el = document.getElementById(id);
  [...values].sort().forEach(v => {
    const opt = document.createElement('option');
    opt.value = v; opt.textContent = v;
    el.appendChild(opt);
  });
}

function render() {
  const domain = document.getElementById('domainFilter').value;
  const func = document.getElementById('functionFilter').value;
  const type = document.getElementById('typeFilter').value;
  const search = document.getElementById('searchBox').value.toLowerCase();

  const filtered = allClusters.filter(c => {
    if (domain && !(c.tags.domains || []).includes(domain)) return false;
    if (func && !(c.tags.joint_functions || []).includes(func)) return false;
    if (type && c.tags.type !== type) return false;
    if (search) {
      const haystack = (c.tags.subject + ' ' + c.articles.map(a => a.title).join(' ')).toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });

  const list = document.getElementById('cardList');
  list.innerHTML = '';
  filtered.forEach(c => list.appendChild(renderCard(c)));
}

function renderCard(cluster) {
  const div = document.createElement('div');
  div.className = 'card';

  const tagsHtml = [
    ...(cluster.tags.domains || []).map(d => `<span class="tag">${escapeHtml(d)}</span>`),
    ...(cluster.tags.joint_functions || []).map(f => `<span class="tag function">${escapeHtml(f)}</span>`),
    cluster.tags.type ? `<span class="tag type">${escapeHtml(cluster.tags.type)}${cluster.tags.subject ? ': ' + escapeHtml(cluster.tags.subject) : ''}</span>` : '',
  ].join('');

  const highlightsHtml = (cluster.tags.highlights || []).map(h => {
    const src = cluster.articles[h.source_index];
    const link = src ? `<a href="${src.url}" target="_blank">[${escapeHtml(src.source)}]</a>` : '';
    return `<div class="highlight">${escapeHtml(h.point)}${link}</div>`;
  }).join('');

  const sourcesHtml = cluster.articles.map(a =>
    `<a href="${a.url}" target="_blank">${escapeHtml(a.source)}</a>`
  ).join(' &middot; ');

  div.innerHTML = `
    <div class="card-date">${cluster.date}</div>
    <div class="tags">${tagsHtml}</div>
    ${highlightsHtml}
    <div class="sources">Sources: ${sourcesHtml}</div>
  `;
  return div;
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

document.getElementById('domainFilter').addEventListener('change', render);
document.getElementById('functionFilter').addEventListener('change', render);
document.getElementById('typeFilter').addEventListener('change', render);
document.getElementById('searchBox').addEventListener('input', render);

load();
"""


def main():
    clusters = load_all_clusters()
    write_data_json(clusters)
    write_static_files()
    print(f"Built site with {len(clusters)} clusters into docs/")


if __name__ == "__main__":
    main()
