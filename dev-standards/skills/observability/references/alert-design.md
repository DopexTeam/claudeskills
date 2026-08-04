# Alert design — what deserves a page vs. a dashboard

Human attention is the scarcest resource in the system, and alerts spend it. Every
alert is a claim: *this is worth interrupting someone for.* The design question is
never "can we detect this?" — almost everything is detectable — it's "what response
does this condition actually deserve?"

## The three tiers

| Tier | Deserves it when | Examples |
|---|---|---|
| **Page** (interrupt a human now) | User-impacting **now** AND requires human action **now** AND there's a runbook for that action | Error-rate SLO burning, queue age past promise, payment processing down, dead-man switch fired |
| **Ticket** (next working session) | Real, needs a human, but no one's night improves by knowing at 3am | DLQ slowly accumulating, cert expiring in 2 weeks, disk 70% and climbing slowly |
| **Dashboard** (looked at when investigating or reviewing) | Context, not conditions — the shape someone consults *after* a signal | Throughput, latency percentiles, saturation, queue depth, staleness |

The failure mode runs one direction: everything gets promoted to page, pages become
noise, and within weeks all of them are ignored — including the real one. An alert
that fires and gets dismissed twice is either demoted or fixed; **muted-forever is
not a tier**, it's a deleted alert still paying rent.

## Page on symptoms, not causes

Page on what users experience — error rate, latency SLO burn, work not completing
(queue age, staleness) — not on internal states that *might* cause it (CPU%, memory,
pod restarts). Cause-based pages fire when nothing is wrong and sleep through novel
failures; symptom-based pages fire exactly when someone should care, whatever the
cause turns out to be. The causes belong on the dashboard the responder opens next.

Prefer **burn-rate / sustained-duration** conditions over instant thresholds: "error
rate above 5% for 10 minutes," not "one spike crossed a line." Single-sample
thresholds page for blips and teach dismissal.

## Alert on absence

The deadliest production failure is silence: the scheduler that stopped firing, the
backfill that hung, the webhook source that quietly stopped sending. Nothing errors —
there's just no data. Every periodic process gets a **dead-man switch**: it emits a
heartbeat (event or metric), and the alert fires when the heartbeat *stops*. An
error-based alert can't catch a process that isn't running.

## Every page carries its runbook

A page without a next action just wakes someone to feel bad. The alert links the
runbook for exactly that condition (the house `RUNBOOK-*.md` format, where
`project-artifacts` is installed — including its half-success modes, which is where
alert responses actually go wrong). No runbook writable? Strong sign it's a ticket or
a dashboard, not a page.

## What belongs on the dashboard

For a worker/pipeline system, the investigating human wants, in order: **is work
completing** (throughput, success/failure by `job_kind`), **is it keeping up** (queue
depth AND queue age — depth without age hides a stuck consumer), **what's failing**
(error rate by `outcome` and `stage`, DLQ depth), **how fresh** (staleness: now minus
newest completed item), **how hot** (saturation: workers busy, DB connections, rate-
limit headroom). Percentiles over averages throughout — p95/p99 is where users live;
the average is where problems hide.
