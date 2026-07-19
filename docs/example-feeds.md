# Example Feeds for Abundroid

A starter list of RSS/Atom feeds relevant to the abundance ecosystem, for
operators choosing Sources. This is a seed for a larger curated list, not a
finished one — treat the "To verify" section as leads, not confirmed feeds.

**Only add a feed after confirming it returns real RSS or Atom.** Open the URL in
a browser: a working feed shows plain XML beginning with `<?xml` or `<rss`, not a
styled web page. See "How to find a feed" in
[SETUP.md](SETUP.md#2-test-collection-locally).

## Verified (returns valid RSS, checked 2026-07)

| Organization | Feed URL | Focus | Notes |
|---|---|---|---|
| Hypertext (Niskanen Center) | `https://hypertext.niskanencenter.org/feed/` | Public goods, markets, state capacity | Substack; feed at `/feed/` |
| Sightline Institute | `https://www.sightline.org/feed/` | Housing, zoning, clean energy | Strong for state/local legislation |
| Institute for Progress | `https://ifp.org/feed/` | Permitting, science funding, state capacity | Tracks federal reform bills |
| Employ America | `https://www.employamerica.org/rss/` | Macro and labor-market policy | Fed/monetary focus more than legislation; feed at `/rss/` |

These four are also the seeded/example Sources in
[`data/sources.csv`](../data/sources.csv).

## Aggregators and discovery feeds (verified 2026-07)

Single feeds that surface many sources at once. Useful for discovery, but
higher-noise, so lean on the review queue.

| Source | Feed URL | Focus |
|---|---|---|
| Works in Progress | `https://www.worksinprogress.news/feed` | Progress studies: growth, science, cities |
| Construction Physics | `https://www.construction-physics.com/feed` | Building, infrastructure, construction cost |
| Statecraft | `https://www.statecraft.pub/feed` | How government actually implements policy |
| Slow Boring | `https://www.slowboring.com/feed` | Abundance-adjacent politics and policy |

**Google News query feed (a technique, not one feed).** Google News turns any
search into an RSS feed:

```
https://news.google.com/rss/search?q=YOUR+QUERY&hl=en-US&gl=US&ceid=US:en
```

For example `q=YIMBY+housing+legislation` returns cross-outlet coverage. Powerful
for topic monitoring, with caveats: results are noisy and off-topic items appear,
links are Google redirect URLs, and Google may rate-limit heavy use. Treat it as
a discovery source that leans hard on human review, not a clean publisher feed.

## To verify (candidates — confirm the feed before adding)

Named during planning but not yet checked. Try the org's site, then `/feed/`,
`/rss/`, or a "Subscribe" link:

- Mercatus Center (permitting, regulation)
- Center for Growth and Opportunity
- Economic Innovation Group (EIG)
- Abundance Institute
- Regional and national YIMBY organizations (housing legislation)

## iCal calendar Sources (usable now, `ical` format)

Abundroid's iCal adapter (v1) reads `.ics` calendar feeds directly, so these no
longer wait on a future adapter — add them as Sources with **Format** set to
`ical` and **Default Kind** set to `event`. The adapter only picks up concrete,
dated events; **recurring events (those defined with an `RRULE`) are skipped
in v1**, so a Source built from a recurring meeting series will only surface
occurrences that are also published as standalone (non-recurring) entries.

- **Legistar meeting calendars** — e.g., the San Francisco Board of Supervisors
  Legistar calendar offers `.ics` exports and works as an `ical` Source today.
  Legistar RSS (`Feed.ashx`) exists on some older portals but requires a live
  per-jurisdiction subscription URL and is jurisdiction-dependent; most
  flagship portals have moved to iCal-only. The Legistar **Web API** (bill text
  and status, not just meeting calendars) is a separate integration and
  remains **Tier 2** on the
  [roadmap](ROADMAP.md#feedback-candidate-directions).
- **Event calendars** — most event platforms (Eventbrite, Meetup) dropped RSS;
  they expose iCal or an API. Their `.ics` exports now work as `ical` Sources,
  subject to the same recurring-event caveat above.

## Expanding this list

A fuller "good abundance feeds" list is a research task worth doing deliberately:
survey abundance-adjacent organizations, confirm each feed, and tag by topic
(housing, energy/permitting, transit, science/innovation, state capacity) and by
geography (federal, state, local). Add confirmed results to the Verified table.
