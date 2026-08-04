# Touch ergonomics — targets, thumbs, and field conditions

The numbers, their sources, and the conditions that move them. Ergonomics is physics
plus anatomy: a capacitive screen reports a contact patch, a thumb sweeps an arc, and
neither cares about the design's intentions.

## Target sizes — the table

| Standard | Minimum | Notes |
|---|---|---|
| Apple HIG | 44×44 pt | Hard floor on iOS |
| Material 3 | 48×48 dp, ≥8dp gap | Hard floor on Android |
| WCAG 2.2 — 2.5.8 Target Size (AA) | 24×24 CSS px | A legal/compliance floor-of-floors, not a design target |
| WCAG 2.2 — 2.5.5 (AAA) | 44×44 CSS px | Roughly the platform floors |
| **Comfortable, real-world** | **48–56dp** | Primary actions, moving users |
| **Gloved / field work** | **56–64dp, ≥12dp gaps** | See field conditions below |

**Hit area ≠ visual size.** A 24dp glyph with a 48dp touch area is correct (RN:
`hitSlop`; web: padding on the touchable, not the icon). The reverse — a large-looking
control whose real touchable is the small inner element — is the classic hidden miss.

## The thumb map

Most phone use is one-handed, thumb-driven. The reachable zone is a fan centered on
the bottom corner of the gripping hand:

- **Easy:** bottom third, center-weighted. Primary actions, main navigation, the
  submit button live here.
- **Stretch:** middle of the screen, opposite bottom corner.
- **Hard:** top corners — top-left is worst for right-thumb grips. Anything placed
  there is a two-handed operation; on large screens it may be out of reach entirely.

Consequences: bottom sheets beat top menus; bottom navigation beats top tabs for
touch (independent of platform idiom, which agrees); a screen's one critical action
belongs bottom-center or bottom-trailing.

**Miss-cost asymmetry:** a destructive action adjacent to a frequent one converts a
2mm miss into data loss. Separate them spatially (different zone, not just 8dp), and
prefer **undo after** to **confirm before** — confirmation dialogs get muscle-memoried
into "always tap OK" within a week; undo stays effective forever.

## Field conditions — what moves the numbers

- **Gloves** widen and blur the capacitive contact patch: accuracy is bought with
  target size (56–64dp) and spacing (≥12dp), not user care. Long-press becomes
  unreliable (contact wobble resets the timer) — never gate anything important on it.
  Some work gloves don't register at all: minimize typing, prefer big
  choice-buttons, steppers, and scanning over free text.
- **Sunlight** crushes contrast: aim ≥7:1 for text and critical affordances, avoid
  subtle gray-on-gray states, and don't encode meaning in color alone (which is also
  the color-blindness rule — sunlight just enforces it on everyone).
- **Movement and vibration** (walking a site, in a vehicle) degrade precision like
  gloves do: bigger targets, and forgiveness — autosave drafts continuously; phone
  calls, dead batteries, and drops are normal events mid-form, and a lost 20-minute
  inspection is a trust-ending failure.
- **Wet screens** produce phantom touches: debounce critical actions, and make
  anything destructive require a deliberate, distinct interaction.
- **One-handed is the default assumption** for field tools — the other hand is
  holding a ladder, a clipboard, or a flashlight.

## Gestures — the accessibility rules

- Every gesture has a visible, tappable alternative (WCAG 2.5.1: no multipoint or
  path-based gesture as the only way). Swipes and long-presses are accelerators,
  never the only door.
- Keyboard behavior is ergonomics too: focused fields scroll into view above the
  keyboard, forms advance field-to-field (return-key/IME actions), and the submit
  control remains reachable while the keyboard is up.
