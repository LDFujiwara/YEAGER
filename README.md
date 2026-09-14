# Intel News Board

An automated, free, hands-off news aggregation and tagging site. A GitHub
Actions workflow runs daily: it pulls articles from major wire services,
defense/natsec trade press, and topic searches; groups articles likely
covering the same event; tags each group by Domain (Land/Air/Sea/Space/
Cyberspace), Joint Function (per JP 3-0), and Type (threat-actor/tech/
policy); and extracts a few factual highlights with links back to the
original source. The result publishes as a static, filterable site via
GitHub Pages.

This tool only gathers, groups, and tags — it does not assess, judge, or
draw conclusions about the material.

## One-time setup

1. **Create the repo.** Push everything in this folder to a new GitHub
   repository (public or private — your call).

2. **Get a free Gemini API key.** Go to [Google AI Studio](https://aistudio.google.com/apikey),
   sign in with a Google account, and click "Create API key." No credit
   card required for the free tier used here.

3. **Add it as a repo secret.** In your repo: Settings → Secrets and
   variables → Actions → New repository secret. Name it exactly
   `GEMINI_API_KEY`, paste in the key, save.

4. **Enable GitHub Pages.** In your repo: Settings → Pages → under
   "Build and deployment," set Source to "Deploy from a branch," branch
   `main`, folder `/docs`. Save. GitHub will give you a URL like
   `https://<username>.github.io/<repo-name>/`.

5. **Trigger a test run.** Don't wait for the schedule — go to the
   Actions tab, click "Daily Intel Pull" in the left sidebar, click
   "Run workflow" (top right), and run it manually. Watch it complete,
   then check your Pages URL a minute or two later.

After that, it runs automatically every day at 11:00 UTC (edit the `cron`
line in `.github/workflows/daily-pull.yml` to change the time).

## Customizing

- **Feed list**: edit `GENERAL_FEEDS`, `DEFENSE_NATSEC_FEEDS`, and
  `LOCAL_REGIONAL_FEEDS` in `scripts/pull_articles.py`. Add any RSS feed
  URL you trust.
- **Search topics**: edit `SEARCH_TOPICS` in `scripts/run_pipeline.py`.
- **Daily volume cap**: `max_clusters` in `categorize.py`'s
  `tag_all_clusters()` — currently 40/day, comfortably inside Gemini's
  free-tier daily limit. Raise it if you're not hitting rate limits;
  lower it if you are.
- **Clustering sensitivity**: `overlap_threshold` in `corroborate.py` —
  lower groups more aggressively (more false-positive groupings), higher
  groups more conservatively (more near-duplicate separate entries).

## Notes on the free tier

Gemini's free tier (used here via `gemini-2.0-flash-lite`) has no credit
card requirement but does have daily/per-minute request caps that Google
can change. If tagging starts failing, check
[Google's current published limits](https://ai.google.dev/gemini-api/docs/rate-limits)
— you may just need to lower `max_clusters`.

## Architecture

```
.github/workflows/daily-pull.yml   Scheduled + manually-triggerable Action
scripts/pull_articles.py           RSS feeds + topic search, no API key needed
scripts/corroborate.py             Groups likely-same-event articles
scripts/categorize.py              Gemini tagging: domain/function/type/highlights
scripts/run_pipeline.py            Orchestrates the above, writes data/<date>.json
scripts/build_site.py              Builds docs/ (static site GitHub Pages serves)
data/                              One JSON file per day, accumulates over time
docs/                              Generated site — GitHub Pages source
```
