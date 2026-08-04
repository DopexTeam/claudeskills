---
name: architecture-inquiry
description: "Interrogate a project's architecture before any code exists: establish the domain shape before choosing technology, hunt the single load-bearing decision, separate settled from open from deferred with rejected alternatives attached, derive invariants with their named catastrophes, name the anti-scope, produce a de-risking phase, and surface real calendar time. Use this whenever the user is starting a new project, service, or major feature, or says anything resembling \"how should I build this,\" \"what stack,\" \"help me design,\" \"architecture,\" or presents a greenfield brief — even when they appear to want code immediately, and especially then. Never supplies a domain fact; unknowns are marked as questions for the human."
---

# Architecture Inquiry

The moment before code exists is the cheapest a project will ever be to change — and
where the most expensive mistakes are made, because nothing pushes back yet. This skill
is the interrogation that belongs in that moment. It ends at a decision record. It
writes no code, ever. The pull to "just start the schema" is strongest exactly when the
inquiry hasn't happened, because unanswered questions feel like momentum waiting to be
spent — especially then, interrogate first.

## Posture

- **Interrogate; don't propose.** The deliverable is decisions the human can own, with
  their alternatives and reasons attached — not a recommended architecture delivered
  from authority. A proposal ends the conversation; a sharp question improves the answer.
- **Never supply a domain fact.** Tenant counts, approval flows, billing rules, what
  happens to a rejected invoice — if it isn't known, ask. An invented domain fact looks
  identical to a real one in the record, and everything built downstream inherits the
  invention silently. Unknowns enter the record as explicitly marked questions for the
  human. It is always better for the record to say "unknown" than to be plausibly wrong.
- **Domain shape before technology.** Entities and their real cardinalities, who moves
  money, the tenancy model, tolerance for failure — these answer most technology
  questions on their own. A stack chosen first is chosen by familiarity and defended
  retroactively. When the user arrives stack-first ("Next.js + Supabase, sound good?"),
  treat the stack as a hypothesis: establish the domain shape, then check whether the
  stack survives contact with it — and say that's what you're doing, because "sound
  good?" deserves its real answer: *the domain decides; here is what I need to know.*
- **Ask in batches, load-bearing first.** A wall of forty questions stalls the human;
  one question per message drips for a week. Ask the few whose answers gate everything
  else, each with one line on why it matters; park the rest in the record as open
  questions with what they're blocking.

## The method — seven moves, in order

`references/question-bank.md` holds domain-shape questions by system type;
`references/invariant-catalog.md` holds recurring invariant classes. The record (see
Output) accumulates as you go.

### 1. Establish the domain shape

Before any technology word: the entities and their **real** cardinalities (numbers the
human gives, not aspirations), the actors and what each may do, where money moves, the
tenancy model, read/write asymmetry, data lifetime (edited? deleted? audited?
retained?), the integration surfaces, and what a worst-case failure costs — in dollars,
trust, or law. Pull the type-specific questions from the question bank; ask what the
bank doesn't cover if the domain demands it.

### 2. Hunt the single load-bearing decision

Every project has one decision that, if wrong, invalidates most of the others — the
tenancy model, the source of truth, the sync direction, the consistency boundary. Name
it in the record and spend disproportionate effort on it. Decisions are not equal, and
a process that treats them equally spreads attention evenly across wildly unequal risk.
The test: for each candidate, ask *"if this turned out wrong in month three, what else
falls?"* The one where the answer is "most of it" is the one.

### 3. Sort every decision: settled / open / deferred

- **settled** — decided now, with rationale and rejected alternatives attached. A
  decision recorded without its rejected alternatives will be re-litigated the moment
  the reason it won is forgotten.
- **open** — needs the human; recorded as a question, with what it blocks.
- **deferred** — deliberately postponed, with the named trigger that forces it
  ("revisit at the first tenant over 10k users"). Deferred without a trigger is just
  forgotten with extra steps.

### 4. Derive invariants, each with its named catastrophe

From the domain, not from a best-practices list: what must never happen in *this*
system? State each in one quotable sentence and attach the concrete catastrophe —
"tenant A's invoices appear in tenant B's portal," not "data integrity issues." An
invariant without a catastrophe gets traded away in the first performance conversation;
one with a catastrophe defends itself. Use the catalog as a prompt, not a checklist to
copy: every invariant included must be justified by a domain answer from move 1.

### 5. Name the anti-scope

What this system deliberately does not do — the adjacent features everyone will quietly
assume are included (the reporting module, the mobile app, the public API). Scope creep
negotiates against silence; the anti-scope is the sentence you point at. Record rejected
scope with reasons, exactly like rejected alternatives.

### 6. Produce the de-risking phase

Order the first phase of work by what kills the riskiest assumption fastest, not by
what demos best. If the load-bearing decision rests on an assumption — the external API
can actually deliver that data, the sync can really be one-way — phase one exists to
prove or bury that assumption with the smallest possible build. A demo that runs on top
of an untested assumption is a demo *of the assumption*.

### 7. Surface real calendar time

List everything gated by an external party's clock: API access approvals, OAuth app
review, app-store review, client data delivery, credential provisioning, procurement.
At agent speed everything else feels hours away, so the calendar-gated items *are* the
schedule — and each should be initiated before phase one starts, not when it blocks.

## Output

One decision record containing: the domain shape as established (facts, with unknowns
marked as questions), the load-bearing decision, every decision sorted
settled/open/deferred with rejected alternatives, the invariants with catastrophes, the
anti-scope, the de-risking phase, the calendar list, and the prioritized question batch
for the human.

The *format* of that record belongs to `project-artifacts`: where it's installed, write
into its `DECISIONS.md` and `ASSUMPTIONS.md` templates. Where it isn't, produce the
same content under those headings in plain markdown — the record must exist either way,
because an inquiry that lives only in the conversation evaporates when the session ends.

## Where this skill stops

- **At the record. No implementation of any kind** — no scaffold, no schema, no "quick
  prototype to explore." The record is the deliverable; the first line of code is a
  different task, governed by other skills.
- **It does not review its own output.** Critique of the resulting design belongs to
  the `adversary` subagent, where installed — a context with no stake in the design
  passing. Grading your own inquiry finds only the gaps you already knew about.
- **It has no opinion on how anything looks.** Aesthetic and UI direction belong to
  `design-workflow` and `frontend-design`, where installed. The inquiry may record that
  a UI exists and what it must accomplish, never its appearance.
- **The inquiry itself ends.** When the load-bearing decision is settled — or
  explicitly parked open with a de-risking step attached — stop interrogating and hand
  over the record. Not every question needs an answer today; every question needs a
  place in the record.
