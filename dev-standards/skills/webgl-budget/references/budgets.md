# Budgets — tunable starting numbers

Starting points, not laws: tune per project, but tune **before** the scene is built
and record the tuned numbers in the decision record. A budget adopted after the scene
exists always fits the scene. Every number is verified per `verification-discipline`'s
performance pattern: throttled or real reference device, sustained run, percentiles.

## Reference device

A mid-tier Android roughly three years old (the audience's phone, not the dev
laptop). Desk proxy: Chrome DevTools 4–6× CPU throttle + a capped DPR — useful for
iteration, never for the final claim. iOS check on the oldest supported iPhone;
Safari is also where context loss and memory limits bite first.

## Frame time — sustained, not first-30-seconds

| Metric | Budget |
|---|---|
| p95 frame time, mobile reference device | ≤ 20 ms (~50fps floor), **sustained over a 3+ minute interactive session** |
| p95 frame time, desktop | ≤ 16.7 ms |
| Thermal signature | If p95 degrades > 30% between minute 1 and minute 3, the scene is over budget regardless of its opening numbers |
| Input-to-response (drag, option change) | ≤ 100 ms |

## Payload and loading

| Metric | Budget |
|---|---|
| 3D runtime JS (three/R3F/drei + scene code), gzipped | ≤ 300 KB, **lazy-loaded** — never in the page's initial bundle |
| Hero/configurator model (Draco or meshopt glTF) | ≤ 2 MB |
| Textures, total, KTX2 | ≤ 4 MB desktop / 2 MB mobile |
| Total initial 3D payload | ≤ 6 MB desktop / 3 MB mobile |
| Time to first rendered frame (4G, reference device) | ≤ 3 s, with the poster painted immediately while it loads |
| Page interactive | Never blocked by the 3D payload — the page works before the scene arrives |

## Scene complexity

| Metric | Mobile | Desktop |
|---|---|---|
| Draw calls | ≤ 100 | ≤ 300 |
| Triangles | ≤ 300 k | ≤ 1 M |
| Texture memory (GPU) | ≤ 128 MB | ≤ 512 MB |
| Realtime lights | 1–2 max; bake or use an environment map for the rest | same |
| Realtime shadow maps | 0–1, small | 1–2 |
| Particles | ≤ 10 k, instanced | ≤ 100 k, instanced |
| Device pixel ratio | capped at 1.5 | capped at 2 |
| Postprocessing passes | Each full-screen pass is budgeted like a light: count them, justify them | same |

## The two non-numeric budget lines

- **Battery:** a scene that only renders on demand (static until touched) costs
  near-zero between interactions; a 60fps idle loop on a static scene is pure battery
  burn. `frameloop="demand"` (R3F) or equivalent is the default for anything that
  doesn't move on its own — which, under `prefers-reduced-motion`, is everything.
- **Memory over time:** GL memory must be flat across mount/unmount cycles
  (`renderer.info.memory` — geometries and textures return to baseline after
  dispose). A leak here surfaces as context loss on iOS long before any crash report
  names it.
