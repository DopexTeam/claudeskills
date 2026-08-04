# Architecture — <project name>

<!--
Developer-facing. The reader survived the README quickstart; this is their second hour.
- Link decisions by ID (D-###) from DECISIONS.md where it exists — never restate the
  rationale here; two homes for one decision will drift apart.
- Quote invariants EXACTLY as recorded. Paraphrased invariants accumulate loopholes.
- Everything here is observed from the code as it is. Unknowns are marked "unknown",
  not smoothed over.
-->

## Overview

<One paragraph: the shape of the system — what comes in, what goes out, what stores
state, what it depends on. If a diagram helps, a small mermaid block here.>

## The pieces

| Component | Responsibility | Where |
|---|---|---|
| <name> | <one line> | `<path>` |

## The main flow

<Walk the primary path end to end — a request, a job cycle, an event — naming the file
or function at each hop. One flow, told properly, beats six summarized.>

## Key decisions

| Decision | Record |
|---|---|
| <what was chosen> | D-### <or "undocumented — see gap list / ask"> |

## External dependencies

| System | Used for | When it's down |
|---|---|---|
| <API/service> | <purpose> | <actual observed behavior — degraded? broken? unknown?> |

## Invariants a contributor must not break

<Quoted exactly from the decision record, with the catastrophe attached — the reason
travels with the rule.>

## Deliberately not here

<The anti-scope: what this system does NOT do, so nobody "helpfully" adds it. Link the
decision record entry if one exists.>
