"""
Entry point run by the daily GitHub Actions workflow. Pulls articles,
clusters likely-same-event coverage, tags each cluster via Gemini, and
appends the day's results to data/ as a dated JSON file.
"""
import json
import os
import sys
from datetime import date

from pull_articles import pull_all
from corroborate import cluster_articles
from categorize import tag_all_clusters

# Topics for the search-based pull, on top of the fixed RSS feed list.
# Edit this list to change what the topic search specifically looks for.
SEARCH_TOPICS = [
    "cyberspace operations",
    "space force news",
    "defense policy",
    "geopolitical tensions",
    "cyber threat actor",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print("Pulling articles...")
    articles = pull_all(SEARCH_TOPICS)
    print(f"Pulled {len(articles)} unique articles.")

    print("Clustering by likely shared event...")
    clusters = cluster_articles(articles)
    print(f"Grouped into {len(clusters)} clusters.")

    print("Tagging via Gemini...")
    tagged = tag_all_clusters(clusters, api_key)
    print(f"Tagged {len(tagged)} clusters.")

    os.makedirs(DATA_DIR, exist_ok=True)
    today = date.today().isoformat()
    out_path = os.path.join(DATA_DIR, f"{today}.json")
    with open(out_path, "w") as f:
        json.dump(tagged, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
