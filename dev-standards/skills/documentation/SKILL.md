---
name: documentation
description: "Write reader-facing documentation from evidence, matched to its audience: technical documentation for developers — README, architecture overview, API reference, contributor onboarding — and end-user documentation — the user manual, feature guides, and task-oriented how-tos that explain what the software is for and how to use it, in the reader's vocabulary rather than the builder's. Use this whenever the user asks for docs, a README, a manual, a guide, onboarding material, or help content, whenever software will be used by people who didn't build it, and whenever a shipped change makes existing reader-facing docs wrong. Documents only what exists and can be shown to work; aspirations are marked as roadmap, never described as features."
---

# Documentation

Documentation is a product surface: for a new developer it *is* the codebase's first
hour, and for an end user it *is* the software's voice. This skill writes for readers
who weren't in the room — which is exactly why it has one non-negotiable core: **write
from evidence, for the reader you actually have.** Everything else is register and
template.

## First move: identify the reader, then the document

The reader determines everything — vocabulary, structure, even what counts as truth
(see `references/audience-registers.md`). Only then pick the document:

| The request | Reader | Template |
|---|---|---|
| "Write a README", "help someone get started with the repo" | Developer, minute 0–10 | `assets/README.md` |
| "How does this system work", contributor onboarding | Developer, hour 2 | `assets/ARCHITECTURE.md` |
| "Document the API", integration docs | Developer (integrator) | `assets/API.md` |
| "User manual", "how do people use this", help content | End user | `assets/USER-MANUAL.md` |
| "Write a guide for <feature>" | End user | `assets/FEATURE-GUIDE.md` |

Copy the template; keep its comment block — it carries the rules to the next writer.
When a request spans audiences ("document this project"), that's two documents, not one
hybrid: a hybrid serves neither reader and reads as written for the author.

## The docs-from-evidence rule

Document only what exists and was observed working:

- **Run every command before writing it.** A quickstart that fails on step 2 teaches
  the reader to distrust every page that follows — the doc is dead from that moment,
  it just hasn't been deleted yet.
- **Capture, don't recall.** API examples are captured responses (scrubbed), not
  prose-from-reading-the-handler — middleware and serializers shape the real response.
  UI labels and status names are transcribed from the running product, not from the
  code's internal names, which drift from what the screen ends up showing.
- **What can't be verified gets marked, or asked.** "Unverified" and "unknown — ask" are
  legitimate entries; a plausible guess is not. If the product can't be run or seen
  from here, say so and ask for access, screenshots, or captured output — never
  document from imagination.
- **Aspirations are roadmap, never features.** Future work appears under an explicit
  Roadmap heading in future tense, or not at all. A manual describing a dead or
  unbuilt feature is the canonical unearned claim — and the reader who hits it stops
  believing the features that *do* exist.

## Register: the reader's words, exactly

The full treatment is in `references/audience-registers.md`; the two rules that carry
most of it:

- **End-user docs use the screen's exact labels** — if the button says "Submit", the
  manual says Submit, in quotes, never a synonym — and no builder vocabulary at all
  (no endpoint, database, sync, config). The user's document should never remind them
  code exists.
- **Developer docs use the repo's exact names** — `reconcile_stale_wars`, not "the war
  cleanup job" — so grep works and ambiguity dies.

## Placement

`README.md` stays at the repo root — it is the landing page, and it should carry the
code-level handoff plus a pointer to the index, not the index itself.

Everything else goes in the `docs/` tree that `project-artifacts` owns:
**`docs/reference/`** for developer docs that describe current state (architecture
overview, API reference, stack conventions), and **`docs/user/`** for end-user
documentation. `docs/README.md` is the index — add an entry there when you add a
document, because a document nothing points at does not exist.

End-user docs default to `docs/user/`, but the delivery channel wins if one exists —
a help site, a client folder, in-app content. What does not vary: they are written in
the reader's vocabulary, using the screen's exact labels.

Follow the project's existing convention over any of this. A second documentation home
splits the truth, and reorganizing someone's docs while writing one is a scope
violation — see `change-scoping`.

## Update triggers — docs are wrong the moment behavior changes

A shipped change carries a question: *which reader-facing document did this just make
wrong?* Renamed a status → user manual's status table and any feature guide showing
it. Changed an endpoint or its shape → API reference. New env var → README
configuration table. Changed a user flow → the manual's task steps. Update the doc in
the same change, or log the debt explicitly — a stale doc is worse than a missing one,
because a missing one at least doesn't lie.

## On existing, undocumented projects

Pair with `project-adoption` (where installed): run adoption first, and its record —
observed decisions, reconstructed runbook, gap list — becomes the evidence base for
the architecture doc and README. Where the *why* is unknown, the docs say what the
adoption record says: `undocumented — see decision record`, never a rationale invented
for narrative flow.

## Boundaries

- **Internal project memory is not reader-facing documentation.** Decision records,
  assumption logs, runbooks, handoffs, and the design ledger belong to
  `project-artifacts` — a runbook is an operator's procedure, not a user manual, even
  when the same human wears both hats. This skill's documents may *link* those, never
  absorb them.
- **This skill documents verified behavior; it doesn't verify.** Whether a check
  actually proves the behavior is `verification-discipline`'s bar, where installed.
  What this skill enforces is refusing to document what lacks the evidence.
- **Why the code is the way it is** — when nobody remembers — is `project-adoption`'s
  archaeology, not this skill's to invent.
- **How a docs *site* looks** — theme, layout, visual design — belongs to
  `design-workflow` / `frontend-design`, where installed. This skill owns the words.
