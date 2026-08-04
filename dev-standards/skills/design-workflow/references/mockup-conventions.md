# Mockup conventions — the spec format

The mockup exists to be reviewed, revised, and then obeyed. These conventions keep it
cheap to read, cheap to change, and unambiguous to build from. (What the mockup should
*look like* is `frontend-design`'s question; this file only governs the container.)

## One self-contained file

One `.html` file: inline CSS in a `<style>` block, inline JS only if an interaction
genuinely needs demonstrating. No build step, no framework, no CDN or external
requests — it must open from disk in any browser and render identically as a
claude.ai artifact (whose CSP blocks external hosts anyway). Self-contained is what
makes it reviewable anywhere, diffable, and disposable.

## Tokens at the top

The first thing in the `<style>` block is the complete token set as CSS custom
properties on `:root` — colors, type families and scale, spacing, radii. This block
*is* the design-system proposal: a reviewer reads the whole system in twenty lines
before seeing it applied, and the build later lifts the block wholesale. Names match
what the components will use (`--color-ink`, `--space-3`), not mockup-throwaway names.
Every color and size below the block derives from a variable — a hardcoded hex
mid-file is a token that escaped review.

## Real content

Populate with the domain's real material — actual invoice numbers, real vendor names,
plausible amounts, the true status vocabulary — never lorem ipsum or `$1,234.56`.
Placeholder content hides exactly the failures a mockup exists to catch: the vendor
name that wraps, the amount that overflows, the status label longer than its badge.
(Grounding in the subject is also `frontend-design`'s first rule; the mockup is where
it gets enforced.)

## The states that will actually happen

A screen isn't specified by its happy path. Include, on the same page or via a
trivial toggle, whichever of these the screen will really hit: **empty** (first run,
no data), **loading**, **error**, **the long case** (overflowing text, large counts,
many rows), and permission-reduced variants if roles differ. A reviewer approving
only the happy path has approved a fifth of the screen.

## Annotated for review

Make the mockup carry its own review agenda:

- A comment block at the top: what this screen is, which ledger tokens it consumes
  vs. proposes, and the **open questions** the reviewer must answer.
- `<!-- NOTE: ... -->` at each decision point in the body — the places where a choice
  was made that the reviewer might want to unmake.

The annotations are what elevate the file from "a picture" to "a spec with its
questions attached."

## Naming and retention

`mockups/<screen>-<direction>-<date>.html` (e.g.
`mockups/invoice-approval-ledger-a-2026-08-02.html`). Rejected mockups are not
deleted — the file plus its one-line rejection reason in the DESIGN ledger is the
record that stops the direction being re-proposed in a month. The approved mockup is
named in the ledger as the spec of record for the build.

## The floor still applies

The mockup demonstrates the quality floor rather than deferring it: responsive at
phone width, visible keyboard focus, `prefers-reduced-motion` respected. (The floor
itself is `frontend-design`'s; a mockup that hides a floor violation ships that
violation into the build with a signature on it.)
