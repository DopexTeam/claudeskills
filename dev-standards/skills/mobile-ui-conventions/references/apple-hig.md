# iOS idiom — distilled from the Apple Human Interface Guidelines

The distillation is for working from; when a control's exact behavior matters, check
the current HIG (developer.apple.com/design) — it moves with each iOS release.

## Units and layout

- Points (pt), not pixels. Minimum touch target **44×44pt**. Standard screen margins
  16pt; grouped content uses inset, rounded sections.
- Safe areas everywhere: status bar / Dynamic Island top, home indicator bottom,
  ears in landscape. Read insets from the system; they change per device.

## Navigation grammar

- **Tab bar** (bottom, 2–5 items): top-level destinations. Icons + short labels;
  tabs persist state; switching tabs is never destructive.
- **Navigation bar** (top): title, back at top-left, at most a couple of trailing
  actions. Large titles collapse on scroll.
- **The left-edge back swipe is load-bearing.** Full-screen horizontal gestures or
  edge-anchored carousels that swallow it make the app feel broken.
- **Modality is a sheet.** Self-contained tasks present as sheets (with grabber,
  pull-to-dismiss); full-screen modals are for immersive tasks only. A modal always
  has an explicit exit (Done/Cancel) in addition to pull-down.

## Type

- System font is **SF Pro** (+ SF Symbols for icons — thousands of glyphs that match
  the type metrics). Use **Dynamic Type text styles** (Body = 17pt default, Title,
  Caption, etc.) rather than raw sizes, so user text scaling works for free.
  Practical floor: 11pt for anything readable; body content at Body, not below.

## Controls and idioms — the things that make a screen feel iOS

- Grouped inset lists with chevron disclosure for drill-in rows; swipe actions on
  list rows (leading/trailing); pull-to-refresh.
- Switches for booleans (never checkboxes); segmented controls for 2–5 exclusive
  options; context menus on long-press (with a visible alternative for the action).
- Alerts are rare and binary; action sheets for choices arising from an action.
- Haptics via the feedback generators, sparingly — success, warning, selection tick.
- Blur/material backgrounds behind bars; content scrolls under them.

## Motion

- Spring physics, interruptible; sheets slide up, pushes slide from trailing edge.
- Respect the Reduce Motion setting (crossfade instead of slide/zoom).

## App Store note

Apps that egregiously break platform expectations (trapped navigation, broken text
scaling, ignored safe areas) draw review friction and one-star "feels like a web
page" reviews — idiom violations are a business cost, not just a taste issue.
