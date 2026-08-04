# Audience registers — writing for the reader you actually have

Two readers, two registers. The method is identical — write from evidence — but what
counts as evidence, what organizes the document, and what the words are allowed to be
all change with the reader. Most bad documentation is good documentation aimed at the
wrong reader.

## The two readers

**The developer** wants mechanism: what runs where, what talks to what, what command
does what, and what will break if they touch it. They can read code — the docs exist
to save them from having to read *all* of it, and to carry the things code can't say
(why, invariants, boundaries).

**The end user** wants outcomes: how to get their task done, whether it worked, and
what to do when it didn't. The stack is invisible and irrelevant to them. They will
never read the code, and nothing in their document should remind them it exists.

## The register table

| | Developer docs | End-user docs |
|---|---|---|
| Organizing unit | Component, endpoint, flow | Task ("How do I…") |
| Vocabulary | The repo's exact names (`SqlStore`, `/api/ingest`) | The screen's exact labels ("Submit", "Pending review") |
| Perspective | "The service polls every 6 hours" | "Your dashboard updates several times a day" |
| Failure framing | Error codes, logs, where to look | "What you'll see, what it means, what to do" |
| Precision | Exact — versions, paths, limits, types | Honest but rounded — "up to a day", "large files may take a while" |
| Evidence | Commands run, output captured, code read | The running product: real screens, real labels, real statuses |
| Success criteria | Reader can modify the system safely | Reader completes the task without asking anyone |

## Tells that a doc is aimed at the wrong reader

Any of these means stop and re-aim:

- A user manual containing **endpoint, database, null, payload, sync, config, schema,
  cache** — or any word the UI itself never shows.
- A README explaining what a button does, or narrating UI flows — that's the manual's
  job; the developer needs the mechanism behind the button.
- User-facing steps that mention files, environment variables, or restarting anything
  (unless the product genuinely asks users to do that — in which case the *product*
  has the register problem, which is worth flagging).
- Marketing adjectives in either register ("blazing fast", "seamless"). Docs describe;
  they don't sell. An adjective is a claim with no evidence attached.
- Passive system-voice in task docs ("the invoice will then be processed") where the
  user needs to know *who acts* — them, or the system, or another person.

## The translation rule

Every internal name has a user-visible name, and each register uses its own — exactly,
never a synonym:

- If the button says **Submit**, the manual says Submit — not "send", not "upload",
  and never "trigger the ingestion".
- If the status column shows **Pending review**, the statuses table says `Pending
  review` verbatim — a manual that says "awaiting approval" forces the user to guess
  whether that's the same thing.
- In developer docs the same discipline points the other way: the code's names,
  spelled exactly (`reconcile_stale_wars`, not "the war cleanup job"), so grep works.

When writing user docs, transcribe labels from the running product — screenshots or
the live UI — never from memory and never from the code's internal names, which drift
from what the UI ends up showing.

## What "evidence" means per register

The docs-from-evidence rule (see SKILL.md) applies to both readers; the admissible
evidence differs:

- **Developer docs:** a command actually run with its output, a captured API response,
  code actually read. Reading the handler is not evidence of the response shape —
  middleware and serializers shape the real one; capture it.
- **End-user docs:** the running product, seen. A feature described from the spec or
  the codebase — instead of from the screen — is aspiration wearing a manual's clothes:
  the canonical unearned claim.
