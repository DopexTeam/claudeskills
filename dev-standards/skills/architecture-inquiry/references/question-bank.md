# Question bank — domain shape by system type

Questions that establish domain shape, grouped by system type. Ask the universal set
always; add the matching type sections. These are prompts, not a script — skip what the
brief already answers, add what the domain demands. Every question here exists because
its answer changes an architectural decision; if the human asks why you're asking, the
italicized *because* is the reason.

## Universal — every system

1. **What are the entities, and what are their real cardinalities?** Ten tenants or ten
   thousand? Fifty invoices a month or fifty thousand a day? *Because three orders of
   magnitude is the difference between "anything works" and a real design constraint —
   and aspirational numbers produce architecture for a company that doesn't exist yet.*
2. **Who are the actors, and what may each one see and do?** *Because the permission
   model is load-bearing in most multi-actor systems and nearly impossible to retrofit.*
3. **Where does money move, and who is liable when it moves wrong?** *Because anything
   touching money inherits idempotency, audit, and reconciliation requirements that are
   brutal to add later.*
4. **What is the tenancy model — who must never see whose data?** *Because tenant
   isolation is the classic load-bearing decision: wrong in month three, everything falls.*
5. **What already exists?** Spreadsheets, a legacy tool, a vendor system, a manual
   process. *Because "greenfield" is usually a migration in disguise, and the existing
   thing defines the data you must honor.*
6. **What is the read/write shape?** Who writes, who reads, how skewed? *Because a
   10,000:1 read-heavy system and a write-heavy ingest system want different designs
   under the same feature list.*
7. **What is the data's lifetime?** Edited after creation? Deleted — really deleted?
   Retained for law? Audited — who changed what, when? *Because append-only,
   soft-delete, and audit trails are schema-level decisions, not features.*
8. **What breaks, and what does it cost, when this system is wrong or down?** Annoyance,
   money, a legal problem, a safety problem? *Because failure tolerance sets the
   verification, redundancy, and review budget for everything else.*
9. **What must this system talk to?** APIs, webhooks, files from humans, hardware.
   *Because every integration is a calendar item, a failure mode, and a place the
   design doesn't control.*
10. **Who operates this?** Who answers when it breaks at 2am, and what can they do?
    *Because a system operated by its builder and one operated by a client's office
    manager need different amounts of self-explanation.*

## Multi-tenant SaaS / client portal

- Are tenants isolated by contract or by expectation — is cross-tenant leakage a
  breach, or an embarrassment? *Sets how structural the isolation must be.*
- Do tenants share any data on purpose (directories, benchmarks, marketplaces)?
  *Deliberate sharing through an isolation boundary must be designed, not patched.*
- How does a tenant arrive (self-serve signup, sales-led onboarding, migration from a
  legacy system) and how does one leave — what do they take with them? *Onboarding and
  offboarding are where tenancy models get expensive.*
- Who inside a tenant administers the tenant? Can they see everything their users do?
- What is per-tenant customization, really — config, branding, or behavior?
  *Behavioral customization is where "config over code" either holds or dies.*
- What's the biggest tenant this must survive, in users and in data?

## Internal tool / dashboard

- Who looks at this, how often, and what decision do they make from it? *A daily
  operational screen and a monthly executive summary are different systems.*
- What is the source of truth, and may this tool ever write back to it? *Read-only
  against a source of truth is a categorically simpler system — establish whether that
  simplicity is available.*
- How fresh must the data be — real-time, hourly, yesterday? *Because "real-time" that
  actually means "this morning" saves an architecture.*
- What happens when the numbers are wrong — who notices, and what did they already do
  with the wrong number?
- Does anyone outside the org ever see it? *The moment the answer is yes, it stops
  being an internal tool.*

## Data pipeline / integration service

- What is the source of truth for each entity, and who wins when two sources disagree?
  *Conflict resolution is usually the load-bearing decision.*
- Is the flow one-way or two-way? *Two-way sync is an order of magnitude harder;
  confirm it's actually required before designing for it.*
- What are the volumes and arrival patterns — steady drip, daily batch, bursts?
- Can the source deliver what's needed — fields, history, rate limits, webhooks vs.
  polling? *Verify against the source's actual API docs during de-risking, not from
  memory of what the vendor claims.*
- What happens on replay — if the same record arrives twice, or a day's batch is
  reprocessed? *Idempotency is cheap to design in and miserable to retrofit.*
- How far behind is acceptable, and who gets told when the pipeline stalls?

## Mobile / field tool

- What is the connectivity reality — genuinely offline (basements, jobsites), or just
  occasionally slow? *Offline-first is a load-bearing decision that reshapes the whole
  data layer; don't accept "sometimes spotty" without probing.*
- What happens when two people edit the same thing offline? *Conflict strategy must be
  chosen, not discovered.*
- One-handed? Gloves? Sunlight? In a vehicle? *Physical context constrains the UI more
  than brand does — and feeds the mobile conventions skill later.*
- Photos, signatures, GPS, barcode scans? *Each device capability is a permission, a
  failure mode, and a sync payload.*
- Personal devices or company-issued? Which platforms actually matter?

## Marketplace / two-sided

- Which side is scarce, and which side is being subsidized to show up? *The scarce
  side's experience is the actual product.*
- Who sets prices, and who moves money — does the platform hold funds, even briefly?
  *Holding funds triggers regulatory and liability weight worth designing away.*
- What does a transaction's lifecycle look like, including disputes and refunds?
- Can the two sides see each other's identity, history, ratings? What's hidden on
  purpose?

## API as product / platform service

- Who are the callers — internal teams, partners, the public? *Sets the versioning and
  deprecation discipline; a public API's mistakes are permanent.*
- What is the compatibility promise? *"We'll be careful" is not a versioning strategy.*
- Rate limits, quotas, tiers — enforced from day one, or bolted on after the first
  abusive caller?
- What's the smallest surface that's actually needed? *Every endpoint shipped is an
  endpoint supported forever.*

## E-commerce / billing-heavy

- What is the money's exact path — provider, fees, payouts, refunds, chargebacks, and
  who reconciles it against the bank?
- Are amounts ever computed client-side? *They must not be; establish where prices and
  totals live authoritatively.*
- Taxes: which jurisdictions, and whose problem is getting them right?
- Subscriptions: proration, upgrades, dunning, cancellation semantics — what did the
  human actually promise customers?
- What is the reconciliation story — how does anyone learn the books don't match?
