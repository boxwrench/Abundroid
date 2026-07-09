# Abundroid Roadmap

Canonical roadmap, reconciling the two original project briefs (now archived in
`archive/`: *Abundance Ecosystem Events Bot.pdf* and *Abundroid Roadmap
Brief.pdf*). Where this document and the PDFs disagree, this document wins.

Guiding principle: **Build the sturdy event database first. Add intelligence in
layers.** The database is the source of truth. Agents are helpers. Humans
approve important changes.

> Reliable first. Useful second. Agentic third. Public later.

## Phase 1 — MVP Event Pipeline (in progress)

- Organization (source) registry and Topic registry, editable in Airtable by
  non-technical admins; local CSV mode for credential-free development.
- Scheduled Python bot: fetch iCal + RSS sources, normalize events, compute
  deterministic `event_uid`, upsert into the review queue (new uid → Needs
  Review; seen uid → update Last Seen).
- Human review workflow: approve / reject / edit / mark duplicate in Airtable.
- Basic queries via Airtable views (this week, by topic, online-only, by org).
  Natural-language querying is deliberately NOT in the MVP — views cover it.
- Suggested/Watchlist stage on Organizations: a free landing spot for
  maybe-organizations, so future source discovery has somewhere to write.
- Quality-metric fields from day one (per-source approval rate, edited-before-
  approval rate) — cheap now, impossible to reconstruct later, and the evidence
  for when automated helpers deserve more autonomy.
- Airtable-native UX from the start: add-organization form view, review queue
  view, source health view. No custom frontend.

## Phase 2 — Broader Sources + Focused Helpers

- schema.org/JSON-LD adapter (covers Eventbrite, Luma, most WordPress event
  plugins).
- Classifier: keyword/exclusion topic tagging driven by the Topics table, with
  an AI tiebreaker for ambiguous events (prompt built from the live table).
- Deduper: fuzzy cross-organization duplicate flagging (never auto-delete).
- Change detection: previously seen events whose details changed at the source
  get flagged for re-review; disappeared events flagged possibly cancelled.

## Phase 3 — AI Extraction, Health, Automation

- AI-assisted extraction for plain-HTML event pages (grounded fields only,
  content-hash caching). Browser automation stays out of scope.
- Source Health: per-source status including the "historically productive
  source yields 0 events for 3 runs → Needs attention" rule; Run Log table.
- Scheduled runs on GitHub Actions cron; secrets via repository secrets.
- Query Agent: simple natural-language questions over approved events.

## Phase 4 — Digest, Scale, Handoff

- Weekly digest drafted from approved events (human reviews and sends). This is
  a committed deliverable, not a maybe — the digest is the system's visible
  output and the reason anyone adopts it.
- Scale registry to 30–50 organizations; archiving policy for past events.
- **Handoff milestone**: the Abundance Network runs Abundroid on its own
  Airtable base and credentials — documented admin roles (who reviews the
  queue, who manages sources), credential rotation, and a named owner. Done
  means they operate it without the original author in the loop.

## Later (explicitly not for the initial build)

Ideas from the roadmap brief, in rough order of likely value. Each requires the
guardrails noted in the brief (suggest, don't act; publish approved data only;
opt-in only).

- Source discovery agent (scout suggests into the Watchlist stage that exists
  from Phase 1; humans approve).
- Public outputs, feeds first: public calendar page and published iCal/RSS
  feeds of approved events. A REST API only if a partner concretely asks —
  feeds deliver most integration value at a fraction of the surface area.
- Reviewer-feedback loop that *suggests* topic rule changes (never silent).
- Admin agent for registry hygiene suggestions; source reliability scoring
  (built on the Phase 1 quality metrics).
- Ecosystem intelligence: speaker tracking, relationship graph, co-host
  analysis, topic trend dashboard, city/regional mapping, periodic reports.
  Gated on extraction quality, not calendar time — speaker/co-host fields are
  the weakest-extracted data and need months of good Phase 3 output first.
- Personalized alerts and recommendations (opt-in, explainable) — deliberately
  last: they need accounts and preference storage, effectively a second
  product. The digest plus public feeds cover most of this value.
- Multi-ecosystem support: zero code now; the env-var/base-per-deployment
  design already keeps this door open (second ecosystem = second base + second
  cron entry).
