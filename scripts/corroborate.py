"""
Groups articles that are likely covering the same underlying event, so the
site can show "here's the same story corroborated across N outlets"
rather than N separate, disconnected entries.

Deliberately simple for v1: no ML embeddings, no external service — just
shared-keyword overlap between titles. This is a rough heuristic, not a
precise match; it's meant to catch the obvious cases (multiple outlets
covering the same breaking story) rather than every possible relationship.
"""
import re

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with",
    "is", "are", "was", "were", "by", "at", "as", "its", "it", "after",
    "over", "amid", "amid", "says", "said", "new", "how", "what", "why",
}


def _keywords(title: str) -> set:
    words = re.findall(r"[a-zA-Z']+", title.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def cluster_articles(articles, overlap_threshold: float = 0.5):
    """Greedy clustering: each article joins the first existing cluster
    whose title keyword overlap meets the threshold, else starts a new one."""
    clusters = []  # each: {"articles": [...], "keywords": set}

    for article in articles:
        kws = _keywords(article["title"])
        if not kws:
            clusters.append({"articles": [article], "keywords": kws})
            continue

        placed = False
        for cluster in clusters:
            if not cluster["keywords"]:
                continue
            overlap = len(kws & cluster["keywords"]) / min(len(kws), len(cluster["keywords"]))
            if overlap >= overlap_threshold:
                cluster["articles"].append(article)
                cluster["keywords"] |= kws
                placed = True
                break

        if not placed:
            clusters.append({"articles": [article], "keywords": kws})

    return [c["articles"] for c in clusters]
