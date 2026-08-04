---
name: webgl-budget
description: "Decide whether 3D earns its place and enforce a hard performance budget when it does: geometry-as-information versus decoration, 3D never load-bearing, sustained frame targets on mid-tier mobile rather than a dev laptop, bundle and texture weight, instancing and LOD, thermal throttling over long sessions, prefers-reduced-motion, and a static plus no-WebGL fallback path. Use this whenever the user mentions 3D, WebGL, three.js, React Three Fiber, a model, mesh, or scene, a product configurator, a floorplan or spatial view, or any immersive or ambient visual effect — including vague asks like \"make it feel more alive.\""
---

# WebGL Budget

Two items lead because they are the two everyone forgets, and each quietly kills a
shipped scene:

1. **Thermal throttling.** The first thirty seconds on any device are a lie. GPUs
   boost, then throttle 30–50% as the chassis heats; a scene that holds 60fps in a
   demo holds 38 after three minutes in a warm hand. Budgets are *sustained* numbers.
2. **`prefers-reduced-motion`.** When it's set, auto-orbit dies, idle "breathing"
   animation dies, camera drift and parallax die. The scene may still move when the
   *user* moves it — direct manipulation is not the vestibular trigger — but nothing
   moves on its own. This is an accessibility contract, not a style preference.

## The gate: 3D earns its place when the geometry is the information

The question is never "will 3D hurt performance?" — asked that way, by the party who
wants to build it, the answer is always no. The question is: **what does the user
learn from the third dimension that a flat surface can't tell them?**

Earns its place — the geometry *is* the data:

- **Configurator** — the product's shape and options are the purchase decision
- **Spatial/site data** — positions of real things in real space (equipment on a
  jobsite, sensors in a building)
- **Floorplan / walkthrough** — the space itself is what's being evaluated
- **Assembly / sequence** — order and orientation in space carry the instruction

Does not earn its place — decoration wearing 3D's costs: the rotating hero, ambient
particles, the "make it feel more alive" ask. Those costs are real and permanent —
hundreds of KB of runtime, megabytes of assets, battery and thermal drain, a fallback
surface to build anyway, and a maintenance tax — and a 2D signature element (that's
`frontend-design`'s territory, and it's good at it) delivers the same memorability
free of all of them. Prerendered video/image sequences deliver "impressive 3D looks"
with zero WebGL cost and are the honest counter-offer.

The gate is a judgment made *before* any scene code exists. If the human hears the
costs and still chooses decorative 3D, that's their call to make — record it as a
decision (with the budget attached) so it reads as a choice, not a drift.

## Never load-bearing — inherited, not re-derived

The umbrella rule belongs to `integration-adapters`: **externals are never
load-bearing.** The GPU is an external. WebGL can be absent (unsupported, blocked,
disabled), degraded (thermal, low-end silicon), or it can die mid-session (context
loss — a routine event on iOS Safari, not an edge case). So every screen containing
3D must complete its job with the 3D gone — which is what `references/fallbacks.md`
specifies. If a fallback that carries the same information cannot be designed, that
is the gate telling you the 3D was decoration after all.

## The budget — declared before the scene is built

Numbers live in `references/budgets.md` as tunable starting points; the discipline is
that they're **declared up front** in the project's decision record, like any phase
exit criterion — a budget adopted after the scene exists always fits the scene.

- **The reference device is a mid-tier Android phone about three years old** — never
  the dev laptop, whose GPU is 10–20× the audience's. CPU throttling in DevTools is
  the desk proxy; a real device is the truth.
- Budgets cover: sustained frame time (p95, minutes-long, thermal included), initial
  3D payload and time-to-first-frame, draw calls and triangle count, texture memory,
  and battery signature.
- **This skill sets the numbers; `verification-discipline` owns proving them** — its
  performance check pattern (throttled profile, sustained run, p95 not average,
  before/after for any optimization claim) is the required proof, not restated here.

## Spending the budget well

The techniques that buy frame time and payload back, detailed in
`references/asset-pipeline.md`: instancing for anything repeated, LOD on hero assets,
Draco/meshopt-compressed glTF, KTX2 textures, baked lighting over realtime shadows,
on-demand rendering for scenes that only move when touched, and a device-pixel-ratio
cap. Also the runtime disciplines: dispose on unmount (leaked GL memory becomes
context loss), pause rendering when the tab is hidden or the canvas is off-viewport
(battery is part of the budget), and keep `renderer.info` visible in dev so draw
calls and memory are watched, not assumed.

## Boundaries

- **General aesthetic direction** → `frontend-design`, where installed — including
  the 2D signature element that usually replaces decorative 3D, and all 2D motion
  and micro-interactions.
- **Running and proving the performance check** → `verification-discipline`, where
  installed. Numbers set here; proof owned there.
- **The mobile container around the canvas** (touch targets, safe areas, navigation)
  → `mobile-ui-conventions`, where installed; this skill governs what happens inside
  the canvas and what it costs.
- **The live data feeding a scene** (polling, adapters, staleness) →
  `integration-adapters`, where installed — a 3D view of live data is a rendering
  layer on top of an integration, and each layer keeps its own rules.
