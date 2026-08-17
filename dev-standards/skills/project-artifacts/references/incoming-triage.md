# `docs/incoming/` — routing documents authored outside the repo

Work happens in browsers, in other chat sessions, in a lawyer's redline, in a
spreadsheet. Those documents arrive as finished prose with no idea what the repo
already says. `docs/incoming/` is where they land before they are allowed to
become part of the record.

**The folder exists because of one asymmetry:** a document authored outside the
repo was written without the record in view, so it may assert things about the
system that are no longer true, or decide things the record already decided
differently. Dropping it straight into `reference/` launders an outside opinion
into project truth. Triage is the step that stops that.

**The folder's failure mode is becoming a swamp.** A file that sits in
`incoming/` across three sessions is not staged, it is lost. Every triage pass
ends with each file either routed or explicitly parked with a named blocker.

---

## The pass

For each file, in order. Do not batch step 4 — the comparison is per-document.

### 1. Classify

What *kind* of document is this? The kind determines the destination, and it is
usually not what the filename suggests.

| Signal | Kind | Destination |
|---|---|---|
| Numbered entries, settled/open status, rationale | **Decision record** | `decisions/` |
| Describes how something currently works | **Reference** | `reference/` |
| "Paste into Claude Code", scoped task, definition of done | **Session brief** | `sessions/` |
| Legally operative or a draft of one; "attorney review required" | **Legal** | `legal/` |
| Commercial framing for a non-engineer reader | **Business** | `business/` |
| Step-by-step operational procedure | **Ops** | `ops/` |

A document can be two kinds at once — a pricing brief that both *decides* rates
and *briefs* an implementation. Split it: the decisions go to `decisions/` under
their own IDs, the build instructions go to `sessions/`. Do not file one document
in two places; extract and cross-link.

### 2. Preserve the ID namespace

If the incoming document carries its own numbering (`P1`, `R3`, `ADR-007`),
**keep it.** Do not renumber into the project's existing sequence. Two separate
permanent-ID namespaces that never collide are strictly better than one sequence
that had to be rewritten — and every renumber breaks back-references silently.
Record the namespace in `docs/README.md` so the prefix resolves.

### 3. Check the claims against the repo

The document asserts things. Some are decisions (the author's to make); some are
**claims about the system** (the repo's to confirm). Only the second kind gets
checked here, and it must be checked before the document is filed:

- A privacy policy saying "we do not store X" — grep for where X is stored.
- A brief saying "pricing lives in one hardcoded catalog" — verify that's still true.
- An agreement promising a 4-hour response — find the thing that measures it.

**Never file a document whose factual claims you have not checked.** A legal
document is the sharpest case: a false statement about your own data handling is
far easier to prove against you than a vague one. Mark each unverified claim in
place (`[CONFIRM]`) rather than deleting it or guessing.

### 4. Diff against what the record already says

This is the step the folder exists for. For each document, find the existing
documents covering the same ground and name the relationship explicitly:

| Relationship | What it means | Action |
|---|---|---|
| **Net new** | Nothing in the record covers this | Route it. Note the gap it filled. |
| **Fills a gap** | The record has a placeholder or a carried assumption waiting for exactly this | Route it, and **disposition the waiting assumption** — that carry is now resolved. |
| **Extends** | Agrees with the record and adds detail | Route it; link from the existing document. |
| **Contradicts (open)** | Disagrees with something not yet settled | Route it; the open question closes. |
| **Contradicts (settled)** | Disagrees with a settled decision | **STOP.** See below. |

Keeping the incoming file in place while you do this is the point — you need
both texts side by side, and moving it first destroys the comparison.

### 5. Contradicting a settled decision is an escalation, not an edit

The house stop-list forbids invalidating a settled decision without a human. An
incoming document does not get an exemption because it looks authoritative or
because it is newer.

What a session does instead:

1. Name the conflict precisely — which decision ID, which claim in which document, and what each says.
2. Trace the blast radius: what else was built on the settled version. A superseded pricing decision usually means a catalog module, a price map, a public page, and a test all now encode a dead number.
3. Write the supersession as a **proposal** — a new decision entry, drafted but marked `open`, that links back to what it would replace.
4. Surface it and stop. The human settles it.

The old entry is never edited or deleted. IDs are permanent; supersession adds.

### 6. Route, and record the move

Move the file to its destination. Add a provenance line at the top — where it
came from and when, because six weeks later "why does this contradict the spec"
is answered by "it was written in a browser without the repo open":

```markdown
*Origin: browser session 2026-08-11, routed from `docs/incoming/` 2026-08-14.
Claims marked [CONFIRM] are unverified against the codebase.*
```

Then update `docs/README.md`, and log anything you had to decide to route it.

### 7. Drain check

End every pass with each file in one of three states:

- **Routed** — it has a home.
- **Split** — extracted into two or more homes; the original is deleted, because a routed document leaving a copy behind is the two-homes-for-one-fact failure.
- **Parked** — still in `incoming/`, with a **named blocker and owner** written into the file. "Waiting on counsel" is a park. "Not sure where this goes" is not — that is an unmade decision, and it is the session's to make.

---

## Legal documents are a special case

They arrive as drafts, they are not the engineering team's to approve, and they
are dangerous when treated as reference. Three rules:

- **`legal/` documents carry a status line in the first five lines** — `DRAFT`,
  `IN REVIEW`, `EXECUTED`, with a date. A reader must never have to guess whether
  a policy is live.
- **A draft is never cited as though it were binding.** Not in a spec, not in a
  runbook, not in a customer-facing page.
- **They generate engineering work, and that work is not optional.** A privacy
  policy that promises deletion within 30 days is a feature request with a
  deadline. Route the document, then file the work it implies into `sessions/` —
  otherwise the company has published a promise nothing implements.

## What does not go through triage

- **Anything you wrote in this repo this session.** It goes straight to its folder.
- **Vendor documentation and third-party references.** Link them; don't vendor them.
- **Anything with a named successor already in the tree.** That is `old/`'s job.
