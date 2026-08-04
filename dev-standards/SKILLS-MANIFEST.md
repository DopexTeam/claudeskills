# SKILLS-MANIFEST.md

**Owner:** Jason Valadez
**Status:** v1.6 — contract doc for authoring sessions
**Purpose:** This is the decision record for the skill set itself. Every authoring session reads this file first and builds exactly one skill against it. Nothing in a SKILL.md may contradict this document; if a session finds a genuine conflict, amend this file first and note the change under Amendments.

---

## 0. Why this file exists

The constraint on a skill set is not token cost — an idle skill costs roughly 100 tokens, and 30-skill setups run fine. The constraint is **description overlap**. Two skills with fuzzy boundaries misfire more than eight with sharp ones, and duplicated content across skills creates drift.

So the load-bearing content here is not the skill names. It's the **non-scope lines** — for every skill, which sibling owns the adjacent concern. Write those before writing any body.

---

## 1. The category rule

Four different kinds of thing were originally all called "skills." They have different enforcement properties and belong in different places:

| Kind | Home | Why |
|---|---|---|
| **Method** — a procedure Claude executes | Skill | Loads on relevance, which is correct for procedures |
| **Format** — a document schema | Skill with `assets/` templates | Progressive disclosure: template costs nothing until opened |
| **Invariant** — a rule that must never be violated | **Hook + test** | A skill that didn't load is a rule that didn't apply |
| **Disposition** — a stance needing context isolation | Subagent | Its bias must not leak into build mode |
| **Always-on policy** | `CLAUDE.md` | Always loaded; no trigger to miss |

**The principle:** *A skill is documentation that persuades. It does not enforce.* Anything that must hold 100% of the time is a hook or a test, and the skill (if any) exists only to explain why and how to comply.

---

## 2. Authoring conventions

Apply to every skill in this manifest.

- **Structure:** `skill-name/SKILL.md` + optional `scripts/`, `references/`, `assets/`
- **Body length:** under 500 lines. Approaching it means adding a `references/` layer with clear pointers to what to read next.
- **Descriptions are pushy.** Claude tends to *under*-trigger skills. Every description states what it does AND when to use it, in the literal words a real request would contain, with an explicit "use this whenever…" clause. All "when to use" information lives in the description, never in the body.
- **Bodies are imperative**, and explain *why* a rule matters rather than stacking bare MUSTs. Rules with reasons survive edge cases; bare mandates get rationalized around.
- **Write the description last**, after the body. You don't know what the skill actually does until it's written.
- **One home per fact.** If content already lives in a sibling skill or `CLAUDE.md`, reference it — never restate it.
- **Evals:** each skill below ships 2 test prompts. Note that skills only get consulted for tasks Claude can't trivially handle alone, so eval prompts must be substantive multi-step requests, not one-liners.
- **Optimizer:** after a skill stabilizes, run `skill-creator`'s description optimization loop against its eval set and take the `best_description` (selected on held-out score, not train).

---

## 3. Reclassification — where every original item went

Nothing was deleted. Verify against your original list.

| Original proposal | Disposition |
|---|---|
| `architecture-inquiry` | **Skill** — unchanged, core of the set |
| `architect` subagent | **Subagent** — unchanged |
| `adversary` subagent | **Subagent** — merged with `verifier`, takes a target |
| `verifier` subagent | **Merged** into `adversary` (same disposition, different input) |
| `build-session-protocol` | **SessionStart hook + slash command** — a skill loads too late to frame the session |
| `verification-discipline` | **Skill** — unchanged |
| `human-gates` | **PermissionRequest hook** + the escalation stop-list (§7) |
| `integration-adapters` | **Skill** — absorbs `long-running-jobs` |
| `long-running-jobs` | **Merged** into `integration-adapters` |
| `decision-record-format` | **Merged** into `project-artifacts` |
| `runbook-authoring` | **Merged** into `project-artifacts` |
| `tenancy-isolation` | **PreToolUse hook + cross-tenant test** |
| `secrets-handling` | **PreToolUse hook + scanner script** |
| `config-over-code` | **PostToolUse hook + CLAUDE.md line** |
| `client-facing-honesty` | **CLAUDE.md** — was already distributed across three skills; became the umbrella, duplicates deleted |
| `platform-invariants` (proposed bundle) | **Dissolved** — would have been a kitchen-sink skill; the members are hooks |
| "beautiful UI" skill | **Dissolved** — `frontend-design` covers ~70%; remainder split into `design-workflow`, `mobile-ui-conventions`, `webgl-budget` |

---

## 4. Install tiers

Build all of Tier 1 and 2. Install in stages so descriptions get real-use feedback before the next batch lands.

**Tier 1 — build and install now (8)**
`architecture-inquiry` · `project-artifacts` · `debugging-discipline` · `verification-discipline` · `change-scoping` · `testing-strategy` · `observability` · `design-workflow`

**Tier 2 — build now, install when first triggered (5)**
`mobile-ui-conventions` (first mobile screen) · `webgl-budget` (first 3D need) · `integration-adapters` (first external system) · `project-adoption` (first legacy/brownfield adoption — that trigger is already live, so it installs immediately; added v1.3) · `documentation` (first docs/README/manual request; added v1.4)

**Tier 3 — do not build yet (2)**
`codebase-conventions` (build at first brownfield project — currently greenfield, so this is correctly deferred) · `irreversible-changes` (build before the first migration or backfill)

**Installed dependency, not authored:** `frontend-design` from `anthropics/skills`. Read it before writing `design-workflow`, and record the exact commit or version read in the Amendments log at that time, so upstream drift is detectable later. It owns aesthetic direction, type pairing and scale, the compact token system, the two-pass brainstorm→critique→build loop, the quality floor, and interface copy. It also carries an anti-default calibration naming the three looks AI design currently clusters into — do not re-litigate that in a sibling skill.

---

## 5. The skills

### 5.1 `architecture-inquiry` — Tier 1

**Description (paste-ready):**
> Interrogate a project's architecture before any code exists: establish the domain shape before choosing technology, hunt the single load-bearing decision, separate settled from open from deferred with rejected alternatives attached, derive invariants with their named catastrophes, name the anti-scope, produce a de-risking phase, and surface real calendar time. Use this whenever the user is starting a new project, service, or major feature, or says anything resembling "how should I build this," "what stack," "help me design," "architecture," or presents a greenfield brief — even when they appear to want code immediately, and especially then. Never supplies a domain fact; unknowns are marked as questions for the human.

**Owns:** the interrogation method. Decision taxonomy. Invariant derivation. Anti-scope. De-risking sequence.

**Non-scope:**
- Implementation of any kind → nothing; this skill stops at the decision record
- The *format* of its output document → `project-artifacts`
- Adversarial review of the resulting design → `adversary` subagent
- Aesthetic or UI direction → `design-workflow` / `frontend-design`

**Bundled:** `references/invariant-catalog.md` (recurring invariant classes with catastrophes) · `references/question-bank.md` (domain-shape questions by system type)

**Pairs with:** `project-artifacts`. Ship together — this skill produces a document, and without the format its output evaporates.

**Evals:**
1. "I want to build a subcontractor billing portal for a construction client. Multi-tenant, pulls from Procore, subs upload invoices and see approval status. Where do I start?"
2. "Here's my plan: Next.js, Supabase, Vercel, Stripe. Building a scheduling tool for trade contractors. Sound good? Let's start on the schema."

---

### 5.2 `project-artifacts` — Tier 1

**Description (paste-ready):**
> Write and maintain the project's canonical documents using fixed templates: numbered decision records, the ASSUMPTIONS log, operational runbooks, session handoffs, and the DESIGN ledger. Use this whenever a decision needs recording, a runbook or deployment procedure needs writing, an assumption needs logging mid-build, work needs handing off to another session or contributor, or the user asks where something should be documented — and whenever another skill produces output that needs a durable home. Owns document structure only; never makes the decisions it records.

**Owns:** all five document schemas. The `[YOU]` / `[RUN]` split. Decision IDs and non-drifting invariants. The assumption disposition field.

**Non-scope:**
- Making architectural decisions → `architecture-inquiry`
- Making design decisions → `design-workflow` / `frontend-design`
- Running the procedures a runbook describes → the runbook's human
- Deciding *whether* something is verified → `verification-discipline`

**Bundled — `assets/` templates:**
| Template | Contains |
|---|---|
| `DECISIONS.md` | Numbered by ID, status (settled/open/deferred), rationale, rejected alternatives, invariants with named catastrophes |
| `ASSUMPTIONS.md` | Assumption, why it was needed, blast radius if wrong, **disposition: promoted / refuted / carried** |
| `RUNBOOK.md` | `[YOU]`/`[RUN]` split, exact commands, dependency order, irreversible warning *before* the step, half-success modes named |
| `HANDOFF.md` | State, what's proven vs. assumed, next single action, known traps |
| `DESIGN.md` | Resolved tokens, component inventory, directions tried and rejected with reasons, open questions |

**Also bundles:** `references/runbook-failure-modes.md`

**Evals:**
1. "We decided to use per-tenant schemas instead of row-level security. Write that up properly, including what we rejected and why."
2. "Write the deploy runbook for this — some steps I run, some are automated, and the migration step can't be undone."

---

### 5.3 `debugging-discipline` — Tier 1

**Description (paste-ready):**
> Diagnose a failure methodically instead of guess-patching: reproduce it first, form a falsifiable hypothesis before touching any code, instrument before guessing, bisect to isolate, and revert failed shotgun changes rather than layering fixes. Use this whenever something is broken, failing, erroring, flaky, hanging, or "not working," whenever the user pastes a stack trace or error message, whenever a test starts failing, and whenever behavior is unexpected. Use it especially after two attempted fixes have not worked — that is the strongest signal the current hypothesis is wrong.

**Owns:** the diagnostic loop. Reproduction requirements. Hypothesis discipline. Bisection. Instrumentation-before-edit. The revert rule.

**Non-scope:**
- Proving the fix worked → `verification-discipline`
- Keeping the fix diff small → `change-scoping`
- Adding permanent instrumentation → `observability`
- Deciding what tests should exist → `testing-strategy`

**Bundled:** `references/failure-taxonomy.md` (heisenbugs, ordering, cache/staleness, env drift, timezone, encoding, off-by-one-tenant)

**Notes for the author:** the highest-value content is the *stop* conditions — when to abandon the hypothesis, when to revert, when to escalate to a human (see §7). Guess-patching is the default failure mode; make abandoning a theory feel cheap.

**Evals:**
1. "This DAX measure returns double the correct value but only for some warehouses. I've tried three variations and nothing works."
2. "Our webhook handler intermittently processes the same event twice. Can't reproduce locally. Here's the log excerpt."

---

### 5.4 `verification-discipline` — Tier 1

**Description (paste-ready):**
> Prove work actually functions using semantic checks rather than status codes or exit codes: every phase ends in something concretely verifiable, and never describe a check that was not actually run. Use this whenever finishing a task, phase, or pull request, whenever about to report something as done, working, complete, or fixed, whenever the user asks whether something works, and whenever a claim about behavior is about to be made without a command backing it.

**Owns:** the definition of verified. Semantic-over-syntactic checking. The never-claim-an-unrun-check rule. Phase exit criteria.

**Non-scope:**
- What tests to write → `testing-strategy`
- Diagnosing failures the check surfaces → `debugging-discipline`
- Adversarial review of the whole build → `adversary` subagent
- Honesty in client-facing output → `CLAUDE.md` (see §9)

**Bundled:** `references/check-patterns.md` (per-layer: DB, API, UI, background job, data pipeline, 3D/perf)

**Notes for the author:** include the performance-check pattern — a throttled-profile run with real numbers, never "it feels smooth." `webgl-budget` depends on that section existing here rather than restating it.

**Evals:**
1. "The tenant isolation work is done. Confirm it's actually working before I tell the client."
2. "Migration ran and returned success. Are we good to move on?"

---

### 5.5 `change-scoping` — Tier 1

**Description (paste-ready):**
> Keep a diff minimal and reviewable: change only what the task requires, no drive-by refactors, no reformatting untouched lines, no opportunistic renames, one logical change per commit. Use this whenever editing existing files, whenever a fix or feature touches more than one file, whenever the user mentions a PR, diff, commit, or review, and specifically before any edit that is tempting to "clean up while I'm in here." Diff noise is what makes agent-authored work unreviewable, so scope is a correctness property, not a style preference.

**Owns:** diff shape. Commit granularity. The no-drive-by rule. Separating the necessary change from the desirable one.

**Non-scope:**
- Matching existing patterns and idioms → `codebase-conventions` (Tier 3)
- Whether the change is correct → `verification-discipline`
- Whether the change should exist at all → `architecture-inquiry`

**Bundled:** none needed; this should be a short, sharp skill.

**Notes for the author:** the useful move is *routing* the discovered-but-out-of-scope improvement, not just forbidding it. Send it to `ASSUMPTIONS.md` or a punch list so suppressing the refactor doesn't mean losing the observation.

**Evals:**
1. "Fix the timezone bug in the invoice date column. The file's a mess but just fix the bug."
2. "This PR is 40 files. Help me split it into something reviewable."

---

### 5.6 `testing-strategy` — Tier 1

**Description (paste-ready):**
> Decide what to test and how: behavior over implementation, never mock the thing under test, fixtures versus factories, the boundaries worth integration-testing, and what should not be tested at all. Use this whenever writing or reviewing tests, whenever the user asks about coverage, mocks, stubs, fixtures, flaky tests, or "should I test this," and whenever adding a feature where the test approach should be decided deliberately rather than defaulted into.

**Owns:** test-level selection. Doubles policy. Fixture strategy. Flake diagnosis. What not to test.

**Non-scope:**
- Whether the code works right now → `verification-discipline`
- Why a test is failing → `debugging-discipline`
- The tenant-isolation test specifically → owned by the hook in §6 (this skill explains it, the hook enforces it)

**Bundled:** `references/doubles.md` · `references/flake-causes.md`

**Evals:**
1. "Adding Stripe billing. What should I actually test here, and what's a waste of time?"
2. "This integration test passes locally and fails in CI about a third of the time."

---

### 5.7 `observability` — Tier 1

**Description (paste-ready):**
> Instrument code so production failures are diagnosable: structured logs with stable field names, correlation IDs carried across service and job boundaries, what belongs in a log versus a trace versus an alert, and never logging secrets or PII. Use this whenever adding logging or error tracking, wiring up Sentry, building a background job, worker, or integration, and whenever the user asks how they will know something broke or how to debug something that already happened in production.

**Owns:** log structure and field naming. Correlation ID propagation. Log/trace/alert boundaries. Retention and cardinality sanity. The no-secrets-in-logs rule *as guidance*.

**Non-scope:**
- Blocking a secret from reaching a log → the PreToolUse hook in §6 (enforcement, not persuasion)
- Temporary instrumentation added while chasing a bug → `debugging-discipline`
- Progress reporting for long jobs → `integration-adapters`

**Bundled:** `references/field-conventions.md` · `references/alert-design.md` (what deserves a page vs. a dashboard)

**Evals:**
1. "Building an async worker pipeline that backfills files into a vector DB. How do I instrument it so I can tell what failed and where?"
2. "Set up Sentry for this Next.js app — what should I actually be capturing?"

---

### 5.8 `design-workflow` — Tier 1

**Description (paste-ready):**
> Sequence UI work so visual decisions accumulate instead of being re-invented: read the project DESIGN ledger first, hand aesthetic direction to `frontend-design`, produce a reviewable HTML mockup as the spec before writing component code, then record resolved tokens and rejected directions back to the ledger. Use this whenever building or reshaping a UI, page, screen, or component, whenever the user asks for a mockup, layout, or design, and whenever visual decisions need to survive past the current session. Never makes the aesthetic choices itself.

**Owns:** the sequence. Mockup-as-spec. Ledger read/append discipline. Handoff between the claude.ai Design surface and Claude Code (the handoff artifact is `DESIGN.md`, not the tool).

**Non-scope — this one matters most, because the sibling is an installed skill:**
- Palette, typography, layout concept, signature element, anti-default calibration, interface copy → **`frontend-design`**. Delegate explicitly by name in the body. Do not restate any of it.
- The `DESIGN.md` schema → `project-artifacts`
- Platform-native mobile conventions → `mobile-ui-conventions`
- Anything 3D → `webgl-budget`
- Matching an existing component library → `codebase-conventions` (Tier 3)

**Bundled:** `references/mockup-conventions.md` (single-file HTML, no build step, token vars at top, annotated for review)

**Notes for the author:** `design-workflow` and `frontend-design` are **designed to co-fire**, which is the one sanctioned overlap in this set. Keep this skill thin — it is a coordinator. If it starts having opinions about color, it has absorbed its sibling and must be cut back.

**Evals:**
1. "Build the invoice approval screen for the sub portal. Should feel like a serious tool, not a startup landing page."
2. "We picked a palette and type scale two weeks ago in another session. Continue the dashboard using the same system."

---

### 5.9 `mobile-ui-conventions` — Tier 2

**Description (paste-ready):**
> Apply platform-native conventions to iOS and Android interfaces: navigation patterns, touch target sizing, safe areas and insets, gesture conflicts, system fonts and dynamic type, platform-appropriate motion, and the judgment call on when brand identity should override platform idiom. Use this whenever building a mobile app screen, a React Native or Expo UI, or a layout that must work as a real touch interface — and whenever the user mentions iOS, Android, the App Store, tap targets, thumb reach, or mobile navigation.

**Owns:** platform idiom. Touch ergonomics. Safe areas. The override judgment.

**Non-scope:**
- Aesthetic direction → `frontend-design`
- The workflow around it → `design-workflow`
- 3D inside a mobile app → `webgl-budget` (its mobile budget section governs)

**Bundled:** `references/md3.md` · `references/apple-hig.md` · `references/touch-ergonomics.md`

**Agent-facing reference sources:** Material Design 3; Apple Human Interface Guidelines; WCAG 2.2 target-size criteria.

**Evals:**
1. "Build the job-site inspection form as a React Native screen. Field techs use it one-handed with gloves on."
2. "This tab bar works on iOS but feels wrong on Android. What's the right call?"

---

### 5.10 `webgl-budget` — Tier 2

**Description (paste-ready):**
> Decide whether 3D earns its place and enforce a hard performance budget when it does: geometry-as-information versus decoration, 3D never load-bearing, sustained frame targets on mid-tier mobile rather than a dev laptop, bundle and texture weight, instancing and LOD, thermal throttling over long sessions, `prefers-reduced-motion`, and a static plus no-WebGL fallback path. Use this whenever the user mentions 3D, WebGL, three.js, React Three Fiber, a model, mesh, or scene, a product configurator, a floorplan or spatial view, or any immersive or ambient visual effect — including vague asks like "make it feel more alive."

**Owns:** the earns-its-place gate. Every performance budget number. Fallback requirements. Asset pipeline (Draco/KTX2). Motion-preference handling for 3D.

**Non-scope:**
- General aesthetic direction → `frontend-design`
- 2D motion and micro-interactions → `frontend-design`
- Running the perf check → `verification-discipline` (this skill sets the numbers; that skill owns how a check is proven)

**Bundled:** `references/budgets.md` (tunable starting numbers) · `references/fallbacks.md` · `references/asset-pipeline.md`

**Notes for the author — the framing must be inverted from how it was originally requested.** "Use 3D unless there's a notable performance impact" will always resolve to *no notable impact*, because that judgment is made by the party that wants to build it. Invert to: **3D earns its place when the geometry is the information** — configurator, spatial/site data, floorplan, assembly sequence. Decorative 3D is where the cost is unjustifiable and is the majority of what gets built.

State the never-load-bearing rule as **inherited from `integration-adapters`** ("externals never load-bearing") rather than re-derived — same rule, different surface.

The two consistently-forgotten items belong up front: thermal throttling across a 30-second-plus session, and `prefers-reduced-motion` killing auto-orbit and idle animation.

**Evals:**
1. "Add a 3D hero to the marketing site — rotating model of the product, should look impressive."
2. "Client wants a 3D view of the jobsite with equipment positions from live data. Feasible on a phone in the field?"

---

### 5.11 `integration-adapters` — Tier 2

**Description (paste-ready):**
> Wrap every external system behind a typed adapter with a demo implementation, make the demo the loud and obvious failure mode, throw immediately on half-configured credentials, never let an external be load-bearing, and report long-running work honestly — progress reflects real state rather than a timer, results reveal only after verified success, and stalls hand off with an accurate account of where they stopped. Use this whenever integrating a third-party API, webhook, payment provider, or vendor SDK, whenever building a background job, worker, queue, or progress indicator, and whenever an external service could be slow, down, or partially configured.

**Owns:** adapter shape. Demo-impl policy. Half-configured detection. Progress honesty. Stall handoff.

**Non-scope:**
- Where credentials live → the secrets hook in §6
- Instrumenting the integration → `observability`
- Proving the integration works → `verification-discipline`

**Bundled:** `references/adapter-template.md` · `references/progress-honesty.md`

**Evals:**
1. "Wire up the Procore API. OAuth, and it'll be flaky. Need it usable in dev without live credentials."
2. "Long backfill job — a few hours. How should the UI report progress?"

---

### 5.12 Tier 3 — specified, not built

**`codebase-conventions`** — Find the existing pattern and match it before introducing a second way to do the same thing; read before writing; identify the codebase's own idioms for state, errors, naming, file layout, and components. Use when working in an unfamiliar or established codebase. *Deferred: current projects are greenfield. Build at the first brownfield engagement.* Will absorb the UI variant of the same rule (match established tokens and components before proposing new ones), so `design-workflow` should point at it rather than duplicating. Distinct from `project-adoption` (§5.13): adoption reconstructs the missing record for an existing repo; this skill matches idioms while writing new code in one.

**`irreversible-changes`** — Migrations, backfills, expand/contract sequencing, reversibility plans, dry-run requirements, and the class of change that cannot be undone. *Build before the first production migration or backfill.* Given the scale of backfill work in flight, this is closer than it looks.

---

### 5.13 `project-adoption` — Tier 2 *(added v1.3)*

**Description (paste-ready):**
> Bring an existing codebase under the house standard by reconstructing the record that was never written: mine the schema, config, dependencies, git history, CI, and any surviving docs or chat exports for the decisions already made; write them up as a proper decision record with evidence attached; extract the invariants enforced in the wild with their catastrophes; keep observed, inferred, and unknown strictly separate — a rationale without evidence is recorded as unknown, never invented; and finish with the full artifact set plus a prioritized gap list. Use this whenever adopting, auditing, inheriting, or resuming an existing or legacy project that predates the standard, and whenever the user says anything resembling "audit this project," "document what we have," "get this repo up to standard," or work resumes on a codebase with no decision record.

**Owns:** the archaeology method and evidence-reliability ordering. The observed/inferred/unknown split. Retroactive decision reconstruction (entries flagged `reconstructed`). The gap list.

**Non-scope:**
- Document formats → `project-artifacts` (this skill fills those templates; it never defines them)
- Designing what the system *should become* → `architecture-inquiry`; adoption records what *is*, and the first new decision happens after adoption ends
- Judging whether the existing design is good → `adversary` subagent; reconstruction stays neutral or the record inherits the reviewer's bias
- Matching existing idioms while writing new code → `codebase-conventions` (Tier 3)
- Claiming current behavior works → `verification-discipline`; adoption may record "untested," never "working"

**Bundled:** `references/evidence-sources.md` (where decisions hide — schema, config, git history, CI, comments, old docs/chats, the human's memory — reliability-ordered, with the caution that the human interview comes *after* the evidence pass, so memory sharpens rather than anchors)

**Pairs with:** `project-artifacts` (the output lands in its templates) and `architecture-inquiry` (whose decision taxonomy and invariant catalog apply here in reverse — pointed to in prose, not restated).

**Evals:**
1. "Here's a repo we built years ago, before any of this existed. Get it up to the house standard — document what we have and what's missing."
2. "I'm resuming an old client portal. No docs, the original chat sessions are gone, and I don't remember why half of this is the way it is. Where do we start?"

---

### 5.14 `documentation` — Tier 2 *(added v1.4)*

**Description (paste-ready):**
> Write reader-facing documentation from evidence, matched to its audience: technical documentation for developers — README, architecture overview, API reference, contributor onboarding — and end-user documentation — the user manual, feature guides, and task-oriented how-tos that explain what the software is for and how to use it, in the reader's vocabulary rather than the builder's. Use this whenever the user asks for docs, a README, a manual, a guide, onboarding material, or help content, whenever software will be used by people who didn't build it, and whenever a shipped change makes existing reader-facing docs wrong. Documents only what exists and can be shown to work; aspirations are marked as roadmap, never described as features.

**Owns:** audience selection and register (developer vs. end-user voice, structure, vocabulary). Reader-facing document templates. The docs-from-evidence rule. Placement conventions. Update triggers (which doc a change invalidates).

**Non-scope:**
- The five internal schemas (decisions, assumptions, runbooks, handoffs, design ledger) → `project-artifacts`; internal project memory is not reader-facing documentation
- Whether a documented behavior actually works → `verification-discipline`; this skill documents verified behavior, it doesn't verify
- Reconstructing *why* the code is the way it is → `project-adoption`
- The no-unearned-claims umbrella → `CLAUDE.md` (§9), inherited — a manual describing a dead feature is its canonical violation
- Visual design of a docs site → `design-workflow` / `frontend-design`

**Bundled — `assets/` templates:** `README.md` · `ARCHITECTURE.md` · `API.md` · `USER-MANUAL.md` · `FEATURE-GUIDE.md`. **Also:** `references/audience-registers.md` (how developer and end-user docs differ in voice, structure, and vocabulary — and the tells that a doc is written for the wrong reader).

**Pairs with:** `project-adoption` — adopt a legacy repo, then document it; the adoption record is the evidence base the docs are written from.

**Evals:**
1. "Write a README and architecture overview for this repo so a new developer can get productive without me."
2. "The portal goes live next week — write the user manual for subcontractors: what it does, how to submit an invoice, what the statuses mean."

---

## 6. Hooks — enforcement

| Event | Hook | Notes |
|---|---|---|
| `PreToolUse` | Block secret values landing in code, config, or a response | Exit 2 blocks the call. Runs before the permission-mode check, so it holds even under bypass-permissions — which is exactly why secrets belong here and not in a skill. |
| `PreToolUse` | Block session-level `SET app.tenant_id` where `SET LOCAL` belongs | Paired with the cross-tenant test as artifact of record |
| `PreToolUse` | Escalation gate — fires the §7 stop-list via `permissionDecision: "ask"` | *Moved from `PermissionRequest` (v1.5):* PreToolUse runs before the permission-mode check, so the forced ask holds even under bypass-permissions and broad allowlist rules — verified live. PermissionRequest only fires where a dialog would already occur, which is when the gate is least needed. |
| `Stop` | **Fast** semantic gates only, appending real results | See warning below |
| `PostToolUse` | Flag a new component hardcoding business data that belongs in the tenant record | Review heuristic, not a blocker |
| `SessionStart` | Inject the session protocol (one session builds one thing; named contract doc wins; log assumptions, don't stall; §7 stop-list) | `SessionStart` stdout becomes context Claude can see, and re-runs on resume — which is why the session protocol lives here rather than in a skill |

**Warning on the `Stop` hook:** `next build` + RLS test + axe on every Stop will be slow enough to get disabled within a week, and a disabled gate is worse than no gate because you'll believe it's running. Split it — fast checks on Stop, expensive suite in CI. Prompt-type hooks (LLM evaluation) work well on `Stop`/`SubagentStop` for the softer question of whether verification actually happened.

---

## 7. Resolved defect: the escalation stop-list

"Don't stop to ask, log to `ASSUMPTIONS.md`" is the right default and the wrong absolute. Without a stop-list it teaches plowing through decisions that should have escalated, and the assumptions log becomes where bad calls go to be forgotten.

**Stop and ask a human when the action would:**
1. Be irreversible or destructive (drop, truncate, overwrite, force-push, delete)
2. Touch production data or a production environment
3. Change security posture — auth, permissions, tenant boundary, encryption, exposure surface
4. Incur spend or move money
5. Invalidate a **settled** decision in `DECISIONS.md` — as opposed to filling a genuine gap, which is what the assumptions log is for
6. Require a credential the session does not already legitimately hold

Lives in two places: documented in the `SessionStart` injection, enforced by the `PermissionRequest` hook. Items 1, 4, and 6 are live risks the moment Stripe and Azure MCP are connected.

---

## 8. Resolved defect: the return edge

The original pipeline was one-way: design → enforce → build → prove. Nothing handled the most common real event — **the build reveals the decision was wrong.** `ASSUMPTIONS.md` was write-only, with no consumer.

**The return edge:** at session end, every assumption gets a disposition.
- **Promoted** → becomes a numbered decision in `DECISIONS.md`
- **Refuted** → reopens the affected decision, which moves back to `open`
- **Carried** → stays, with a named owner and a re-check trigger

This is what makes the decision record living rather than aspirational. The `disposition` field is required in the `ASSUMPTIONS.md` template for exactly this reason.

**Corrected pipeline:**

```
architecture-inquiry ──> DECISIONS.md ──> hooks enforce invariants
                              ^                      |
                              |                      v
                    (promote / refute)        session builds
                              |                      |
                        ASSUMPTIONS.md <─────────────┘
                              |                      |
                              └──> verification-discipline + adversary
```

---

## 9. `CLAUDE.md` — always-on policy

Content that must never fail to apply, and therefore cannot be a skill.

- **No unearned claims.** Never inflate a number, list a dead feature, fake a progress bar, or describe a check that wasn't run. *(This was `client-facing-honesty`. It was already distributed across three skills; consolidating it here removes the duplication — those skills now inherit rather than restate it.)*
- **Config over code.** Behavior comes from rows; overrides never require a change to core.
- **Secrets:** vault or it doesn't exist. No endpoint or log returns a value. Record who owns the key.
- **Tenant isolation:** `SET LOCAL`, never session-level. The cross-tenant test is the artifact of record.
- **Contract doc wins.** When a named contract document and the conversation disagree, the document wins — say so and stop.

---

## 10. Subagents

**`architect`** — the interrogator. Isolated context so its stop-and-question disposition can't corrupt build mode. Preloads `architecture-inquiry`.

**`adversary`** — the review pass, invoked with a target: `design` or `build`. No stake in the thing passing; output is objections, not approval. Preloads `verification-discipline` when target is `build`.

*Merged from the original `adversary` + `verifier`.* Same disposition, different input. Two subagents means two prompts to keep in sync, and they will drift.

---

## 11. Design references

Split by who can actually use them. The agent can't log into a gallery, and shouldn't be reproducing specific designs from one regardless — galleries are for sharpening *your* brief, not for the skill to imitate.

**Agent-facing — bake into `references/`:**
- Material Design 3; Apple Human Interface Guidelines — mobile platform authority
- WCAG 2.2 and APCA contrast — connects directly to the existing axe gate
- Utopia — fluid type and space scales, concretely computable
- Radix Colors — perceptually-built scales; Radix primitives for accessible component behavior
- *Refactoring UI* (Wathan/Schoger) and Butterick's *Practical Typography* — the two most distillable-to-rules texts
- three.js / React Three Fiber / drei docs; web.dev Core Web Vitals for budget numbers

**Human-facing — your input ritual, not the skill's:**
- Mobbin, Refero — real shipped product flows (onboarding, dashboards, auth, settings, pricing)
- Land-book, Site Inspire, Lapa Ninja — production and landing patterns
- Awwwards, The FWA, Godly — visual craft
- Typewolf — type pairings in the wild

---

## 12. Build order

One skill at a time. Fresh context per skill is the ideal; sequential authoring within one conversation is sanctioned, provided each skill is built against this file rather than against the previous skill's chat — re-read the target skill's entry, including every non-scope line, immediately before starting it, and finish it (evals run, §12.1 updated) before opening the next. This file is the contract doc.

1. `project-artifacts` — everything else writes into its templates
2. `architecture-inquiry` + the `architect` subagent — pairs with 1; the subagent (§10) preloads this skill and was missing from the original schedule
3. `project-adoption` — reuses 2's taxonomy in reverse; live legacy projects make it urgent (added v1.3)
4. `debugging-discipline` — highest per-use payoff
5. `documentation` — pairs with `project-adoption` on legacy repos (added v1.4)
6. `verification-discipline` + the `adversary` subagent
7. `change-scoping`
8. `design-workflow` — read `frontend-design` first, in full
9. `testing-strategy`
10. `observability`
11. `mobile-ui-conventions`
12. `webgl-budget`
13. `integration-adapters`
14. **Hooks — separate session.** Different medium, and they need testing against real diffs to confirm exit-code-2 behavior.

### 12.1 Build status

Update this table at the end of every authoring session. States: `not started` → `drafted` → `evals passed` → `installed`.

| Item | Status |
|---|---|
| `project-artifacts` | installed (2026-08-02 — evals passed; junction into `~/.claude/skills/`) |
| `architecture-inquiry` + `architect` subagent | installed (2026-08-02 — evals passed; skill junctioned, agent copied to `~/.claude/agents/` — re-copy after edits, symlink needs elevation) |
| `project-adoption` | installed (2026-08-02 — evals passed, incl. a live run against the Datapoll legacy repo) |
| `debugging-discipline` | installed (2026-08-02 — evals passed) |
| `documentation` | installed (2026-08-02 — evals passed, incl. real developer-docs run against Datapoll) |
| `verification-discipline` + `adversary` subagent | installed (2026-08-02 — evals passed; agent copied to `~/.claude/agents/` — re-copy after edits) |
| `change-scoping` | installed (2026-08-02 — evals passed, incl. live minimal-diff edit test) |
| `design-workflow` | installed (2026-08-02 — evals passed; `frontend-design` dependency installed from pinned clone, see Amendments) |
| `testing-strategy` | installed (2026-08-02 — evals passed) |
| `observability` | installed (2026-08-02 — evals passed) |
| `mobile-ui-conventions` | installed (2026-08-02 — evals passed; Tier 2, installed immediately per user preference) |
| `webgl-budget` | installed (2026-08-02 — evals passed; gate held in both directions) |
| `integration-adapters` | installed (2026-08-02 — evals passed; completes the skill set) |
| hooks + `build-session` command | installed (2026-08-02 — 47 stdin unit tests incl. real Datapoll secrets diff; live `claude -p` tests: secrets block, escalation ask under bypass, SessionStart injection, config-over-code nudge, tenant-guard at project scope. Stop gate verified by real-transcript replay — `Stop` doesn't fire in print mode on 2.1.220, spot-check interactively per `hooks/README.md`. Both plugins installed via the local directory marketplace (now `standards`, renamed from `dopex` — see v1.6); skill junctions and agent copies migrated to plugin at v1.0.0.) |

**Per-session protocol:**
- Read this manifest. Read the target skill's entry, including every non-scope line.
- Draft the body. Imperative, reasons attached, under 500 lines.
- Write the description last.
- Run the two eval prompts. Add a third if the first two both pass trivially.
- Do not start the next skill until the current one's evals have run and §12.1 is updated.

---

## 13. Implementation mechanics

Decided after v1; recorded here so authoring sessions don't depend on chat history.

### 13.1 Where things live during authoring

Build directly in the future plugin repo — do not stage in `~/.claude/skills/` and move later:

```
dev-standards/                   ← git repo, THE authoring workspace
├── SKILLS-MANIFEST.md           ← this file, at root
├── .claude-plugin/
│   └── plugin.json              ← manifest ONLY; no other files in here
├── skills/
│   └── <skill-name>/SKILL.md    ← one folder per skill, always SKILL.md
├── agents/
│   ├── architect.md
│   └── adversary.md
├── hooks/
│   ├── hooks.json
│   └── scripts/
└── commands/
    └── build-session.md
```

To use skills while the set is still in progress, symlink or copy the finished ones into `~/.claude/skills/`; the repo stays the single source of truth. When the set stabilizes: `/plugin marketplace add <path-or-repo>` and install at **user** scope. No restructuring — the repo already is the plugin.

### 13.2 Scope splits (global vs. project)

The same rule three times — *global for how you work, project for what the system is*:

| Thing | Global (`~/.claude/` or house plugin) | Project (client repo) |
|---|---|---|
| `CLAUDE.md` | No unearned claims; contract doc wins | Tenant isolation; secrets; config-over-code |
| Hooks | Secrets scan (never want a literal key anywhere) | `SET LOCAL` tenant hook + cross-tenant test |
| Skills | All eleven (house standard) | `codebase-conventions` once brownfield; client-specific knowledge only |

The tenant hook and test ship as a second, per-project plugin (`multitenant`), installed only where multi-tenancy exists. It must not live in the house-standard plugin — it would block legitimate SQL on single-tenant projects.

### 13.3 Hook mechanics (for session 12)

- Exit 0 = proceed. **Exit 2 = blocked; stderr is fed back to Claude as the message** — write stderr as an instruction, not a log line.
- All intra-plugin paths use `${CLAUDE_PLUGIN_ROOT}` from day one. Hardcoded paths are the standard reason plugin hooks silently don't fire.
- Windows host: scripts assume a POSIX shell — invoke via Git Bash or WSL in the `command` field, or write PowerShell. Test one hook end-to-end before writing the rest; a wrong shell invocation fails silently.
- `PreToolUse` runs before the permission-mode check, so it holds even under bypass-permissions.
- `SessionStart` and `UserPromptSubmit` are the events whose stdout becomes visible context; `SessionStart` re-runs on `--resume`.

### 13.4 Reload semantics (for every session)

- SKILL.md edits take effect immediately in the current session.
- Edits to hooks, agents, `.mcp.json`, and plugin config do **not** — run `/reload-plugins` or restart. If a hook edit "isn't working," reload before debugging the script.
- A `CLAUDE.md` at plugin root is not loaded as context; always-on policy lives in `~/.claude/CLAUDE.md` and each project repo.
- Plugin skills namespace as `/plugin-name:skill-name` for direct invocation; description-based auto-triggering is unaffected.
- If a skill won't trigger, fix the description, not the body.

### 13.5 Dual-surface distribution (claude.ai)

These skills also target claude.ai, uploaded individually as capability skills. Consequences for every authoring session:

- **Each skill folder is self-contained.** Everything a skill needs lives inside its own folder (`SKILL.md`, `references/`, `assets/`); never reference a file outside the folder by path. A skill must survive being zipped and uploaded alone.
- **Cross-skill pointers are prose, not dependencies.** Write "→ `verification-discipline` owns this" as a sentence that still reads sensibly when the sibling isn't installed — on claude.ai it may not be.
- **Hooks, subagents, and `CLAUDE.md` do not exist on claude.ai.** Everything §6 enforces is persuasion-only in the browser. This raises the stakes on §2's explain-why rule: on that surface the skill body is the entire defense, so bodies must state hook-owned rules (and their reasons) well enough to stand alone, even where a hook owns enforcement in Claude Code.

---

## Amendments

*Log changes here with date and reason. A session that finds a genuine conflict amends this file before proceeding.*

- **2026-08-03 (v1.6):** Renamed everything carrying the `dopex` brand, per owner decision. Plugin `dopex-house-standard` → **`dev-standards`** (owner's choice; bumped to v1.1.0), plugin `dopex-multitenant` → **`multitenant`** (v0.2.0), marketplace `dopex` → **`standards`** — the latter two names were session calls under the owner's "rename all" directive; veto by re-renaming and bumping versions. Repo folders renamed to match. Skill namespace is now `dev-standards:<skill>` and install commands read `<plugin>@standards`. Normative sections (§12.1, §13.1, §13.2) updated; dated amendment entries below retain the old names as historical record. Old installs were uninstalled and `dev-standards` v1.1.0 reinstalled at user scope; the `dopex-multitenant` project-scope install was retired without replacement — it pointed at a dead scratchpad test dir from the hooks session, and real installs happen per client project. Discovered during the rename: the repo has **zero git commits** — flagged to owner, not committed by this session.
- **2026-08-02 (v1.5):** Hooks session (build order 14) completed; set is whole and the plugin route from §13.1 is now live. (a) §6 escalation gate moved `PermissionRequest` → `PreToolUse` with `permissionDecision: "ask"` — PreToolUse precedes the permission-mode check, so the gate holds under bypass/allowlists (verified live under `--dangerously-skip-permissions`). (b) Stop gate implemented as a fast deterministic command hook (edit + completion claim + no check after last edit → block), honoring §6's own speed warning; prompt-type variant deferred. (c) `dopex-multitenant` plugin built per §13.2 (tenant-guard hook + cross-tenant test template), installed at project scope only. (d) Distribution: `dopex` directory marketplace at the working-folder root; `dopex-house-standard` v1.0.0 installed at user scope; the 13 skill junctions and 2 agent copies in `~/.claude/` removed in favor of the plugin (`frontend-design` junction kept — upstream dependency, not ours). (e) `~/.claude/CLAUDE.md` created with the §9 global lines. (f) Hook-iteration gotcha recorded in `hooks/README.md`: the install cache is version-keyed; repo edits require a version bump + `plugin update`, `marketplace update` alone does not refresh it. (g) Known upstream limitation: `Stop` hooks don't fire in print mode (2.1.220) — gate verified by real-transcript replay; spot-check interactively.
- **2026-08-01 (v1.1):** Added §13 implementation mechanics — plugin-repo-as-workspace, global/project scope splits, hook mechanics, reload semantics. Decided in planning conversation after v1; recorded so authoring sessions are self-contained.
- **2026-08-02 (frontend-design pin, per v1.2):** `design-workflow` was authored against `anthropics/skills` commit `b29e7cf65e5cb78a5ac33d582270551bc74a14eb` (2026-07-24). Local clone at `../anthropic-skills` (wrapper folder, sibling of this repo); `frontend-design` junctioned into `~/.claude/skills/` from there. Re-read the upstream file after any `git pull` of that clone.
- **2026-08-02 (v1.4):** Added `documentation` (§5.14, Tier 2) — reader-facing docs for two audiences (developer technical docs and end-user manuals/guides) as one skill, keeping the docs-from-evidence core in a single home. Distinct from `project-artifacts`, which owns internal project memory only. Build order position 5, after `debugging-discipline`; later items renumbered. Tier 2 count 4 → 5.
- **2026-08-02 (v1.3):** Added `project-adoption` (§5.13, Tier 2) — brownfield adoption skill that reconstructs the artifact set for existing/legacy projects via code archaeology, keeping observed/inferred/unknown strictly separate. Requested because live legacy projects (pre-standard, pre-Claude) need to be brought under the standard so development can continue on them. Build order position 3 (right after `architecture-inquiry`, whose taxonomy it reuses); later items renumbered. Tier 2 count 3 → 4, with immediate install sanctioned since the trigger already exists. Boundary against `codebase-conventions` noted in §5.12.
- **2026-08-02 (v1.2):** Added §12.1 build-status tracker. Sanctioned same-conversation sequential authoring in §12 (fresh re-read of the target entry per skill still required). Added §13.5 dual-surface (claude.ai) authoring constraints. §4: pin the `frontend-design` version when `design-workflow` is authored. Fixed §5.4 cross-reference (§8 → §9). Added `architect` subagent to the schedule alongside `architecture-inquiry` — it was defined in §10 but absent from §12. Repo location decided: the plugin repo lives at `dopex-house-standard/` inside the working folder (`d:\ClaudeSoftwareDevSkillz`), keeping the wrapper free for reference material; this manifest moves to the repo root per §13.1.
