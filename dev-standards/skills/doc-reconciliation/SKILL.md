---
name: doc-reconciliation
description: "Reconcile the project's markdown record with reality after work has moved on: sweep the docs/ tree and the root-pinned files for drift, build a drift map from what the session actually changed, rank conflicting sources by authority — settled decisions outrank everything including newer files, the code outranks its descriptions, and among descriptions the most recently edited wins — then apply mechanical index and link fixes immediately but present substantive rewrites as a proposal and wait for approval. Use this at the end of a long or many-file session, whenever the user says the docs have drifted, grown stale, or are out of sync, whenever they ask to reconcile, sync, tidy, or true-up the README, architecture doc, or runbooks after changes landed, and before a handoff when reference docs may lie to the next session. Never rewrites append-only records or session history; a conflict with a settled decision is an escalation, not an edit."
---

# Doc Reconciliation

Every session moves the truth: code changes, decisions land, a runbook step stops
being real. The documents describing the system do not move with it unless something
makes them. Per-change update triggers (the `documentation` skill's territory) catch
the doc the author remembered; this skill is the sweep that catches the ones nobody
remembered — the periodic pass that keeps a many-file record from quietly diverging
into several competing versions of the project.

The pass has a hard shape: **map first, rank second, propose third, edit last.**
A reconciliation that starts editing before it has mapped is just more drift,
harder to detect because it is internally consistent.

## 1. Build the drift map before touching anything

Establish what moved and what claims to describe it:

- **What changed this session (or since the last sweep):** `git diff --name-only`
  and `git log` against the last reconciliation point, plus the docs' own
  modification times. The session's edits are the freshest signal of where the
  truth now lives.
- **The full doc surface:** `docs/README.md` (the index), every folder in the
  `docs/` tree, the root-pinned files (`README.md`, `CLAUDE.md`, `AGENTS.md`,
  `ONBOARDING.md`), and any stray `.md` that escaped the tree.
- For each document that *describes current state*, ask one question: **does the
  thing it describes still exist as described?** Spot-check the load-bearing
  claims — commands, paths, names, statuses, flows — against the repo. Do not
  reread every file end to end; drift hides in specifics, so chase the specifics
  the session's changes could have invalidated.

The output of this step is a drift map, not edits: per document — the stale claim,
what the authoritative source now says, and how far apart they are.

## 2. Rank sources by authority — recency is bounded, not absolute

When two sources disagree, the winner is decided by *kind* first, recency second:

1. **Settled decisions outrank everything, including newer files.** A freshly
   edited doc that contradicts a settled entry in `DECISIONS.md` is not evidence
   the record is stale — it is the stop-list's "invalidate a settled decision"
   case. Name the conflict (decision ID, claim, source), draft the supersession
   as a new entry marked `open`, surface it, and stop. Never "sync" the record to
   match a newer description, however recent or confident it reads.
2. **The system outranks its descriptions.** Code, schema, config, and observed
   behavior are what *is*; every doc is a claim about it. When doc and repo
   disagree and no settled decision is implicated, the repo wins and the doc is
   the drift.
3. **Among descriptions, the most recently edited wins.** Files written or
   updated during this session were authored with the current truth in view, so
   they outrank older descriptions of the same ground. This is the only place
   recency confers authority — and it applies to *descriptions* only. A decision
   is never outranked by being old.

## 3. Some files are never reconciled — they are the record, not a description

| File class | Why it never gets "fixed" | What happens instead |
|---|---|---|
| `DECISIONS.md`, `ASSUMPTIONS.md` | Append-only, permanent IDs | Supersede with a new entry; never rewrite |
| `sessions/` handoffs and briefs | Snapshots of a moment; editing one falsifies history | Leave them — current truth lives in `reference/` |
| `old/` | Archive | Nothing. If it is wrong, it was wrong then too |

The reconciliation surface is the overwrite-in-place class: `reference/`, `ops/`
runbooks, the README(s), `user/` docs, and the index.

## 4. Classify each finding, then gate the edits

Three severities, three different permissions:

- **Mechanical** — the index missing an entry, a dead link, a pointer to a
  renamed file. Apply immediately and list what was applied. Asking permission
  for a link fix trains the human to rubber-stamp, which erodes the gate that
  actually matters below.
- **Substantive** — a doc describing a removed component, an invalidated
  quickstart, a changed procedure, two docs disagreeing about current state.
  **Propose, do not apply.** Present the batch — per document: the stale claim,
  the authoritative source, the proposed edit, and what breaks if the edit is
  wrong — then wait for the human. Ten documents rewritten unsupervised is not
  reconciliation; it is a second opinion overwriting the first.
- **Contradiction with a settled decision** — escalation per step 2. Neither
  conflicting document is edited; the only write is *appending* the supersession
  proposal (a new entry marked `open`) to the decision record, and nothing else
  moves until the human rules.

Runbooks get the strictest treatment inside the substantive class: a runbook is
read while something is on fire, so a wrong "fix" there has the highest blast
radius of any doc edit. Propose runbook changes individually, never buried in a
batch.

## 5. While applying approved edits

- **Docs-from-evidence still applies.** Verify a claim before writing it — run
  the command, check the path (`documentation` owns the rule). Replacing stale
  claims with plausible ones has negative value: the doc now *looks* current.
- **Minimal diffs.** Fix the stale claims; do not restructure, re-voice, or
  reformat the document while in there (`change-scoping` owns this). A
  reconciliation diff should read as a list of corrected facts.
- **Chase duplication, not just staleness.** When the same fact drifted in two
  documents, syncing both copies treats the symptom — the disease is two homes
  for one fact. Fix it in its rightful home and turn the other copy into a link
  (`project-artifacts`' one-home rule).

## 6. Close the pass

- Update `docs/README.md` if any document was added, moved, or newly linked — a
  corrected doc the index doesn't point at is still lost.
- Anything found but not resolved — a parked contradiction, a doc that may
  belong in `old/`, a fact with no clear home — gets logged (assumption or open
  decision), not remembered.
- **Diagnose repeat offenders.** A document that drifts every pass is telling
  you something: its facts live in two homes (merge them), or nobody reads it
  (candidate for `old/` — flag it; retiring a document is the human's call).

## Boundaries

- **The tree layout and the five internal schemas** → `project-artifacts`. This
  skill sweeps the tree; it never redefines it. Moving a stray root file *into*
  the tree is a recorded decision, not a reconciliation side effect — flag it,
  don't move it.
- **Register and evidence rules for the new words** → `documentation`. This
  skill decides *which* docs are stale; that skill governs how replacements are
  written.
- **A record that never existed** → `project-adoption`. Reconciliation maintains
  a record; it cannot conjure one. If the sweep finds no decision record at all,
  the fix is adoption, not a very large reconciliation.
- **Whether the system's behavior is correct** → `verification-discipline`. This
  skill syncs descriptions to the system as it is, right or wrong; finding the
  system wrong is a bug report, not a doc edit.
- **Documents authored outside the repo** → `project-artifacts`' `incoming/`
  triage. Reconciliation sweeps what is already in the tree.
- **It never makes decisions.** Every disagreement it finds is either drift (the
  description loses to the system) or a conflict (escalate). There is no third
  path where reconciliation quietly picks a winner.
