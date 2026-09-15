let allClusters = [];

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

// --- Tabs ---
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    document.getElementById('newsPanel').classList.toggle('hidden', tab !== 'news');
    document.getElementById('assessmentsPanel').classList.toggle('hidden', tab !== 'assessments');
    document.getElementById('newsFilters').classList.toggle('hidden', tab !== 'news');
    if (tab === 'assessments') loadAssessments();
  });
});

let assessmentsLoaded = false;
async function loadAssessments() {
  if (assessmentsLoaded) return;
  assessmentsLoaded = true;
  try {
    const res = await fetch('assessments-index.json');
    const items = await res.json();
    const list = document.getElementById('assessmentsList');
    list.innerHTML = '';
    if (!items.length) {
      list.innerHTML = '<p style="color:#7d8494">No assessments posted yet.</p>';
      return;
    }
    items.forEach(item => {
      const div = document.createElement('div');
      div.className = 'assessment-item';
      div.innerHTML = `
        <a href="assessments/${encodeURIComponent(item.slug)}.html">${escapeHtml(item.title)}</a>
        <div class="assessment-date">${escapeHtml(item.date)}</div>
      `;
      list.appendChild(div);
    });
  } catch (e) {
    assessmentsLoaded = false;
  }
}

load();
