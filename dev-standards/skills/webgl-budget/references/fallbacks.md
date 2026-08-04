# Fallbacks — the scene is optional, the job is not

The rule inherited via `integration-adapters`: externals are never load-bearing, and
the GPU is an external. Every screen containing 3D completes its job with the 3D
absent. The fallback is not an apology screen — it carries the *same information* the
scene carries, because the information (not the rendering) was the point. If such a
fallback can't be designed, the 3D was decoration; revisit the gate.

## The ladder

1. **Poster** — a static image of the real scene, painted immediately. It is also
   the loading state, so it exists in every configuration.
2. **Information fallback** — the no-WebGL path that does the job flat:
   - configurator → option list with per-option product photography
   - jobsite/spatial view → 2D map or plan with positioned markers, plus a list
   - floorplan → the 2D plan itself
   - assembly sequence → step-by-step stills
3. **Full scene** — loaded lazily, entered only when support and budget checks pass.

## When each rung applies — detect, don't assume

- **No WebGL / context creation fails** (unsupported, GPU-blocklisted, disabled) →
  rung 2. Feature-detect by actually creating a context, not by user-agent.
- **`prefers-reduced-motion`** → the scene may still load, but nothing self-moves:
  no auto-orbit, no idle animation, no camera drift. User-driven manipulation stays.
- **Constrained clients** — `Save-Data`, very low device memory, data-saver
  connections → rung 2 by default with an explicit "load 3D view" opt-in; a 3 MB
  payload uninvited on a metered connection is a cost the user didn't agree to.
- **Context loss mid-session** — listen for `webglcontextlost` / `restored` from day
  one; on loss, show the poster with a "reload 3D" affordance. **All application
  state lives outside the GL layer** (React state/store, not scene-graph objects),
  so restoration is a re-render, not a data loss. On iOS Safari this is a routine
  event; an unhandled loss is a white rectangle.

## Loading behavior

Poster paints with the page; the 3D runtime and assets load lazily and never block
page-interactive; progressive where the asset pipeline allows (low-LOD first, refine
in place). The transition from poster to live scene happens only when the first real
frame is ready — never a spinner where the poster could be.

## Keep the poster honest

Generate posters from the real scene (a capture step in the build or content
pipeline), not from a hand-made mock — a drifted poster shows product options or site
layouts that no longer exist, which is an unearned claim rendered at 2× DPR.
