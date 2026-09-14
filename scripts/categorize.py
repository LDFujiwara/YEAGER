"""
Sends each article cluster to Gemini's free tier for tagging and highlight
extraction. This is a gather-and-tag step only — it labels and extracts,
it does not editorialize, assess, or draw conclusions about the material.

Requires GEMINI_API_KEY as an environment variable (set as a GitHub Actions
secret — see .github/workflows/daily-pull.yml).
"""
import json
import os
import time
import requests

GEMINI_MODEL = "gemini-2.0-flash-lite"  # high free-tier RPD, good fit for this volume
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

DOMAINS = ["Land", "Air", "Sea", "Space", "Cyberspace"]
JOINT_FUNCTIONS = [
    "Command and Control", "Intelligence", "Fires", "Movement and Maneuver",
    "Protection", "Sustainment", "Information",
]

PROMPT_TEMPLATE = """You are tagging a news story for an intelligence analyst's reference site. Do NOT assess, judge, or draw conclusions — only extract and categorize what the sources actually report.

Sources (may be one article or several covering the same event):
{sources_block}

Return ONLY valid JSON, no other text, in exactly this shape:
{{
  "domains": [list of 0+ from {domains}],
  "joint_functions": [list of 0+ from {functions}],
  "type": "threat-actor" | "tech" | "policy" | "other",
  "subject": "short subject/actor name if type is threat-actor, or short topic if tech/policy",
  "highlights": [
    {{"point": "one factual highlight, one sentence, in your own words", "source_index": 0}},
    ...2 to 4 of these...
  ]
}}
"""


def _build_sources_block(articles):
    parts = []
    for i, a in enumerate(articles):
        text = a.get("full_text") or a.get("snippet") or ""
        text = text[:2000]  # keep prompt size reasonable
        parts.append(f"[{i}] {a['title']} ({a['source']})\n{text}")
    return "\n\n".join(parts)


def tag_cluster(articles, api_key: str, max_retries: int = 2):
    prompt = PROMPT_TEMPLATE.format(
        sources_block=_build_sources_block(articles),
        domains=DOMAINS,
        functions=JOINT_FUNCTIONS,
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            raw_text = raw_text.strip().strip("```").strip("json").strip()
            tags = json.loads(raw_text)
            return tags
        except Exception:
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return {
                "domains": [], "joint_functions": [], "type": "other",
                "subject": "", "highlights": [],
                "tagging_failed": True,
            }


def tag_all_clusters(clusters, api_key: str, max_clusters: int = 40):
    """Caps at max_clusters/day to stay comfortably inside the free tier's
    daily request limit (RPD varies by Gemini model/account — see Google's
    published limits — adjust this cap if you hit 429 errors)."""
    tagged = []
    for cluster in clusters[:max_clusters]:
        tags = tag_cluster(cluster, api_key)
        tagged.append({"articles": cluster, "tags": tags})
        time.sleep(1)  # stay under per-minute rate limits
    return tagged
