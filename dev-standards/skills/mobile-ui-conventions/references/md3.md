# Android idiom — distilled from Material Design 3

The distillation is for working from; when a component's exact spec matters, check
current MD3 (m3.material.io) — tokens and components evolve.

## Units and layout

- **dp** for dimensions, **sp** for text (sp scales with the user's font size — text
  in dp is a text-scaling bug by construction). 4dp base grid; 16dp screen margins.
- Minimum touch target **48×48dp** with **≥8dp** between targets — the visual glyph
  can be smaller; the touch area cannot.
- Insets: status bar, gesture navigation bar (bottom), and display cutouts are all
  window insets — draw edge-to-edge, then pad by the real inset values.

## Navigation grammar

- **Navigation bar** (bottom, 3–5 destinations): active destination shows the pill
  indicator; icons + labels. This is the MD3 sibling of the iOS tab bar — same
  slot, different anatomy.
- **Top app bar**: screen title and contextual actions; collapses/recolors on
  scroll (surface tint, not just shadow).
- **System back is sacred** — button, gesture, and **predictive back** (the peek
  preview as the user drags): every screen must respond sensibly; back is never
  trapped or repurposed. "Back" (system, chronological) and "Up" (hierarchical, in
  the app bar) are distinct and both must work.
- **Navigation drawer** is for secondary/rare destinations only; it is no longer the
  primary pattern.
- **FAB**: the screen's single primary action, when one exists — bottom trailing (or
  centered/extended with a label). One per screen, or none.

## Type and color

- System stack is Roboto (or the OEM's default); the **type scale is role-based** —
  Display / Headline / Title / Body / Label, each with a defined size/weight — map
  content to roles, not to raw sizes.
- MD3 color is **tonal**: roles like `primary`, `surface`, `surfaceVariant`,
  `onPrimary` drawn from tonal palettes; elevation renders as surface *tint* more
  than shadow. **Dynamic color** (palette derived from the user's wallpaper) is an
  Android-native personalization: support it or deliberately opt out — record which.

## Controls and idioms — the things that make a screen feel Android

- **Ripple** feedback on every touchable (iOS-style opacity dims read as unresponsive
  on Android).
- **Snackbar** for transient feedback with optional action (Undo) — the platform's
  forgiveness pattern; there is no iOS equivalent, don't port toasts to iOS.
- Filled/outlined **text fields** with floating labels and helper/error text below.
- **Chips** for filters and small choices; **bottom sheets** (standard and modal) as
  the Android modality workhorse; dialogs rare and binary.
- Checkboxes exist and are idiomatic (unlike iOS); switches for settings.

## Motion

- **Emphasized easing** tokens; **container transform** for element-to-screen
  transitions; durations roughly 200–500ms by size of change.
- Predictive back previews the destination while the gesture is in progress.
- Respect the system's Remove/Reduce animations setting.
