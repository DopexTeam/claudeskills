---
name: design-workflow
description: "Sequence UI work so visual decisions accumulate instead of being re-invented: read the project DESIGN ledger first, hand aesthetic direction to frontend-design, produce a reviewable HTML mockup as the spec before writing component code, then record resolved tokens and rejected directions back to the ledger. Use this whenever building or reshaping a UI, page, screen, or component, whenever the user asks for a mockup, layout, or design, and whenever visual decisions need to survive past the current session. Never makes the aesthetic choices itself."
---

# Design Workflow

Without a sequence, every UI session re-derives the palette, re-invents the type
scale, and re-tries the direction someone already rejected — visual decisions
evaporate at session end and the product drifts toward whatever was decided most
recently. This skill is the sequence that makes design decisions accumulate.

It is a coordinator, and only that. **Every aesthetic question — palette, typography,
layout concept, signature element, anti-default calibration, interface copy — belongs
to the `frontend-design` skill**, which is designed to fire alongside this one. If
this skill ever appears to have an opinion about color, that is a defect in this
skill, not a permission.

## The sequence

### 1. Read the ledger first

Open the project's `DESIGN.md` before any visual thinking happens.

- **Resolved tokens are settled decisions** — reuse them exactly; re-deriving a
  settled token is re-litigating it by accident.
- **Rejected directions are fences** — proposing one again wastes the review that
  killed it. (They're also fuel for better proposals: `frontend-design` itself notes
  that a record of what's been tried helps future passes. The ledger is that record,
  made durable.)
- No ledger yet? Create one from `project-artifacts`' template (where installed;
  otherwise the same headings in plain markdown) — the schema belongs to that skill,
  not this one.

### 2. Hand aesthetic direction to `frontend-design`

Where the ledger leaves gaps — a new project, a new surface, an unresolved axis — the
direction comes from `frontend-design`: its brief-grounding, its token system, its
two-pass plan-then-critique process, its anti-default calibration. This skill's whole
contribution to that step is the handoff itself: give it the brief's real content
*plus the ledger's already-settled tokens and rejected directions as constraints*, so
its choices extend the system instead of restarting it.

On a surface where `frontend-design` isn't installed, the workflow still holds — the
aesthetic choices still get made deliberately against the brief, stated for review,
and recorded; what never happens is a silent default.

### 3. Mockup as spec

Before any component code: one single-file HTML mockup, built to
`references/mockup-conventions.md` (no build step, token variables at the top, real
domain content, key states, annotated for review).

The mockup is cheap on purpose — it opens in a browser in seconds and changes in
minutes, where the same revision to a component tree costs an afternoon and arrives
pre-committed to an architecture. Review happens *here*: the human reacts to a real
rendered screen, and the approved mockup becomes the spec — the contract the build is
checked against. (Adversarial review of a design, where wanted, goes to the
`adversary` subagent; this skill's review step is the human's.)

### 4. Build from the approved mockup

Component code derives from the mockup — its token variables, its structure, its
states — not from a fresh re-imagining in JSX. Where the build must deviate (a
component library constraint, a data reality the mockup missed), the deviation is
flagged back against the spec, not silently absorbed: the mockup-as-spec only works
if the spec stays true.

### 5. Append to the ledger

Before the session ends: write back what was decided. New resolved tokens with their
values and date; components added to the inventory; every direction tried and
rejected, with the reason; open questions with what blocks them. Skipping this step
is how step 1 finds an empty file next session — the append is what the whole
sequence exists to feed.

## Cross-surface handoff

Design work moves between claude.ai (the Design surface, artifacts) and Claude Code.
**The handoff artifact is `DESIGN.md`, not the tool.** A direction explored in the
browser continues in Code by committing its tokens and decisions to the ledger; a
system built in Code continues in the browser by bringing the ledger along. Tokens
travel as text; screenshots and tools don't carry decisions, the document does.

## Boundaries

- **Palette, typography, layout concept, signature element, anti-default calibration,
  interface copy** → `frontend-design`, entirely. This skill hands over and stands
  back.
- **The `DESIGN.md` schema** → `project-artifacts`, where installed.
- **Platform-native mobile conventions** (touch targets, safe areas, navigation
  idiom) → `mobile-ui-conventions`, where installed.
- **Anything 3D** — whether it earns its place, and its performance budget →
  `webgl-budget`, where installed.
- **Matching an established codebase's existing component library and tokens** →
  `codebase-conventions` (a planned sibling; until it exists, the ledger plus
  read-and-match judgment covers it).
- **Proving the built UI works** — rendering, accessibility, performance numbers →
  `verification-discipline`, where installed. An approved mockup is a spec, not a
  verification.
