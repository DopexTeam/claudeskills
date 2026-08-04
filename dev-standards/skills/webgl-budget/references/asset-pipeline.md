# Asset pipeline — where the budget is won or lost

Scene code rarely blows the budget; assets do. The pipeline below runs at **build /
content time** — runtime is too late to fix a 40 MB model, and doing the work on the
user's device spends the very budget it's trying to save.

## Geometry

- **glTF 2.0 is the format.** One format end-to-end; converters exist from
  everything.
- **Compress: Draco or Meshopt** (`gltf-transform`, `gltfpack`). Typical 5–20×
  geometry reduction; meshopt decodes faster and streams better, Draco compresses
  smaller — either is fine, pick one per project and record it.
- **Decimate in the DCC tool first** (Blender's Decimate/remesh): compression can't
  fix a CAD export with 4M triangles of internal bolts. Delete unseen geometry —
  interiors, fasteners, the underside nobody orbits to — target the triangle budget
  *before* export.
- **Merge and instance:** merge static meshes sharing a material (draw calls are the
  budget line, and each mesh is one); use **instancing** for anything repeated —
  fifty pieces of equipment, a hundred trees, ten thousand particles are one draw
  call each as instances.
- **LOD** on hero assets: 2–3 levels, distance-switched (drei `<Detailed>` or
  manual). The full-detail mesh should exist only where the camera can appreciate it.

## Textures

- **KTX2/Basis Universal** (`gltf-transform`, `toktx`) — GPU-native compressed
  formats that stay compressed *in GPU memory* (a 2048² PNG decompresses to ~22 MB of
  GPU memory; the KTX2 version stays ~4 MB). This is the single highest-leverage
  texture decision.
- **2048 max on mobile, 1024 preferred**; power-of-two; mipmaps on. No 4K "just in
  case" — the case never comes and the memory bill always does.
- **Channel-pack** occlusion/roughness/metalness into one texture (ORM — glTF's
  native layout) — three maps for one sampler.

## Lighting

- **Bake what doesn't move:** AO and lightmaps for static scenes; an environment map
  (compressed HDR at low resolution — it's lighting, not scenery) instead of a rack
  of realtime lights.
- Realtime lights are budget lines (1–2 max on mobile); realtime shadows doubly so —
  one small map, or none, with baked/blob shadows doing the grounding.

## Runtime disciplines

- **On-demand rendering** for scenes that move only when touched (`frameloop:
  "demand"` in R3F, manual invalidation in raw three) — the default posture, and
  under `prefers-reduced-motion` effectively mandatory.
- **DPR cap** (1.5 mobile / 2 desktop) — rendering 3× pixels for retina is the
  quietest way to triple frame cost.
- **Dispose discipline:** geometries, materials, textures, and render targets all
  hold GPU memory that survives React unmounts unless `.dispose()` runs. Leaked GL
  memory surfaces as context loss on iOS. Verify with `renderer.info.memory` across
  mount/unmount cycles — the numbers must return to baseline.
- **Pause when unseen:** tab hidden or canvas out of viewport → stop the loop.
  Battery is a budget line, and an offscreen 60fps loop spends it on nothing.
- **Watch `renderer.info` during development** — draw calls, triangles, memory,
  programs — wired into a dev HUD. Budgets that aren't visible during development
  are discovered during the demo.

## Tools, named

`gltf-transform` (inspect/optimize/compress, the swiss-army knife) · `gltfpack`
(meshopt one-shot) · Blender (decimate, bake, delete hidden) · `toktx`/Basis (KTX2)
· three.js `WebGLRenderer.info` (the live meter) · R3F `<PerformanceMonitor>` /
drei `<Detailed>`, `<Instances>` (adaptive quality, LOD, instancing).
