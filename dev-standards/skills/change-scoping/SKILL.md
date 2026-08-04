---
name: change-scoping
description: "Keep a diff minimal and reviewable: change only what the task requires, no drive-by refactors, no reformatting untouched lines, no opportunistic renames, one logical change per commit. Use this whenever editing existing files, whenever a fix or feature touches more than one file, whenever the user mentions a PR, diff, commit, or review, and specifically before any edit that is tempting to \"clean up while I'm in here.\" Diff noise is what makes agent-authored work unreviewable, so scope is a correctness property, not a style preference."
---

# Change Scoping

A reviewer approves what they can read. A 400-line diff wrapped around a 5-line fix
hides the five lines that matter, and whatever the reviewer can't distinguish, they
either rubber-stamp or reject — both failures. Diff noise also degrades the machinery
that comes later: `git blame` stops answering "why is this line like this," and
`git bisect` lands on a commit that changed thirty things. Scope is a correctness
property, not a style preference — this is doubly true for agent-authored work, which
lives or dies on whether a human can review it with confidence.

## The rule

Change only what the task requires. In practice:

- **No drive-by refactors** — including good ones. A good refactor smuggled into a
  bugfix is reviewed as neither: too much noise to review the fix, too little
  context to review the refactor.
- **No reformatting untouched lines.** If the editor's format-on-save rewrites the
  whole file, format only the changed hunks or turn it off for the edit — and if the
  repo genuinely needs a formatter pass, that's its own commit, mechanically pure.
- **No opportunistic renames**, import shuffles, comment-style fixes, or dead-code
  deletion on lines the task doesn't touch. Each one costs reviewer attention exactly
  where it's scarcest: distinguishing load-bearing change from cosmetic.

**The hunk test:** before staging each hunk, ask *"does the task fail without this?"*
If yes, it stays. If no, it's either a separate change (route it — below) or noise
(drop it). A diff where every hunk passes this test reviews in minutes.

## Route the discovery; don't lose it

Suppressing the drive-by refactor must not mean losing the observation — that trade
would be a real cost, and knowing the observation is preserved is what makes
resisting the edit easy. So route it:

- **Default: the punch list.** `PUNCHLIST.md` in the repo (or the project's issue
  tracker): what, where, why it matters, and what task surfaced it. One line each.
- **If it contradicts a recorded decision or assumption**, it's bigger than a punch
  list item — it goes to the assumptions log or reopens the decision (formats belong
  to `project-artifacts`, where installed).
- Then finish the task. The improvement gets its own task later, with its own diff
  and its own review, where it can be judged on its merits instead of smuggled past
  on someone else's.

**The one legitimate exception:** when the mess *blocks* the fix — the bug genuinely
can't be corrected without restructuring. Then the restructure is in scope; say so
explicitly, and split it: commit 1 restructures with zero behavior change, commit 2
fixes. A reviewer can verify "no behavior change" and "the fix" separately; fused,
they can verify neither.

## One logical change per commit

The test: the commit message's first sentence covers *everything* in the commit, with
no "and also." If the sentence needs a second clause, it's two commits.

- **Mechanical and semantic changes never share a commit.** A pure rename, move, or
  formatter pass reviews in seconds *because* the reviewer can trust its purity; mix
  in one behavior change and they must now read every line of both.
- **Refactor-then-fix or fix-then-refactor — never refactor-and-fix.**

## Splitting an oversized PR

When the diff is already too big (the 40-file PR), the method is extraction in
reverse order of reviewability:

1. **Inventory:** `git diff --stat main...HEAD`, then label each file with the logical
   change it serves. Files serving two changes get flagged — they're the split points.
2. **Extract the mechanical layer first** — formatting, renames, generated files,
   lockfiles. Usually most of the line count and the fastest review. Branch from main,
   apply just those changes (`git checkout <big-branch> -- <paths>` pulls whole files;
   entangled files need the hunk-level equivalent), PR it as "mechanical only, no
   behavior change."
3. **Find the dependency spine** of what remains — schema before API before UI — and
   stack the rest as a sequence of PRs in that order, each one logical change, each
   noting what it builds on.
4. **Each split PR gets the one-sentence test** as its description. If a PR in the
   stack can't pass it, split again.

The stack reviews in an afternoon; the original 40 files would have been rubber-stamped.

## Boundaries

- **Whether the change matches the codebase's idioms** — naming, error handling,
  where things live — is `codebase-conventions`' territory (a planned sibling; until
  it exists, read the surrounding code and match it). This skill governs the diff's
  *extent*, not its style.
- **Whether the change is correct** → `verification-discipline`, where installed. A
  minimal diff can still be wrong; smallness proves nothing.
- **Whether the change should exist at all** — the design question — belongs to
  `architecture-inquiry`, where installed. This skill assumes the task is right and
  keeps its footprint honest.
