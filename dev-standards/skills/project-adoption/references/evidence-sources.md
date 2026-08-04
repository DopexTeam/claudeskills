# Evidence sources — where decisions hide, in reliability order

Read top to bottom: the most reliable sources first, so the least reliable are read
against an established picture rather than forming it. For each source: what kind of
decision hides there, and the caution that keeps it from being over-trusted.

## 1. Schema and migrations

The most honest document in the repo — it had to be true for the system to run.
Tenancy model, entity relationships, soft-vs-hard delete, audit columns, unique
constraints, money representation, state fields. Migration *sequence* is a decision
diary: a column added then dropped, an index added in a hurry (look at the dates), a
table renamed — each is a decision event, sometimes a rejected alternative caught in
the act. **Caution:** the schema shows what *is* enforced, not what was *meant* to be;
a missing constraint may be a decision or an oversight — that distinction is exactly
what goes to the interview.

## 2. Configuration and environment surface

Env vars, config files, feature flags, secrets *references* (or, as a gap-list entry,
secrets *values*). This is the system's honest list of external dependencies and
tunable behavior — every var is an integration or a decision someone made configurable.
**Caution:** config accretes; half the flags may be dead. A var consumed nowhere in the
code is archaeology of a *removed* feature, which is its own finding.

## 3. Dependency manifest and lockfile

Every major dependency is a build-vs-buy decision. Versions tell more: a pinned old
major version is either a deliberate hold (find out why) or accumulating risk; a
dependency abandoned upstream is a gap-list entry. Removed dependencies (via git
history of the manifest) are rejected alternatives with dates attached.
**Caution:** presence proves adoption, not active use — check imports before recording
a dependency as load-bearing.

## 4. Git history

The closest thing to the missing rationale. `git log --follow` on a load-bearing file;
merge/PR messages if they exist; revert commits (a rejected alternative, caught live);
bursts of commits on one file (a struggle worth understanding); the dates that turn
"legacy" into a timeline. Author names tell you who to interview if more than one
human was involved. **Caution:** commit messages record what the author *believed* they
did; trust the diff over the message when they disagree.

## 5. CI/CD and deploy artifacts

Workflows, Dockerfiles, IaC, deploy scripts: how this thing actually ships, what gets
tested on every push, what production actually runs. This is the primary source for the
reconstructed deploy runbook. **Caution:** CI that hasn't run green in months describes
the past; check the last successful run's date before recording any of it as current.

## 6. The code's own structure

Directory layout, layering, where validation lives, error-handling idiom, naming.
Structure is a decision made once and then obeyed (or half-obeyed — inconsistency
between old and new areas of the codebase is a timeline, and the boundary between
idioms often dates a change in authorship or approach). **Caution:** structure shows
the *chosen* pattern, not whether it was a good one; record, don't grade.

## 7. Tests

What has tests is what someone once considered worth protecting — a de facto invariant
list. Test names state intended behavior in plain language. **Caution:** absence of a
test is weak evidence of anything; presence of a *skipped* test is strong evidence of a
known, unresolved problem — gap list.

## 8. Comments, TODOs, dead code

TODOs and HACKs are confessions: known gaps, deferred decisions, apologies to the
future. Commented-out code is often a rejected alternative preserved in amber.
**Caution:** comments describe intentions at some past moment, not current behavior —
they rank below the code they annotate. A comment contradicting its code is a finding;
the code is the fact, the comment is the fossil.

## 9. README and docs

Aspirations, setup instructions of varying staleness, sometimes a genuine architecture
note. **Caution:** the README is routinely the least accurate file in a legacy repo —
it describes the project someone hoped to build. Verify every claim against sources 1–6
before recording it as observed; a README claim confirmed nowhere else is at best
*inferred*.

## 10. Old conversations, tickets, chat exports

Prior AI chat sessions, issue threads, Slack fragments — where they survive, they're
the only direct evidence of *why* and of alternatives genuinely weighed. **Caution:**
conversations include options discussed and abandoned without a trace in code; confirm
against the repo which branch of the conversation actually shipped.

## 11. The human's memory — deliberately last

Interviewed after everything above, so the evidence sharpens the questions and memory
fills only the holes evidence can't. Asked first, memory anchors the whole reading —
and memory of *why* is the least reliable record there is, routinely rewritten by
hindsight. Where memory contradicts the evidence, the contradiction itself is the
finding: say it plainly and let the human arbitrate. "I don't remember" converts an
unknown to *confirmed forgotten* — a real answer that stops future digging.
