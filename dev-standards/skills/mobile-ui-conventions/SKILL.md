---
name: mobile-ui-conventions
description: "Apply platform-native conventions to iOS and Android interfaces: navigation patterns, touch target sizing, safe areas and insets, gesture conflicts, system fonts and dynamic type, platform-appropriate motion, and the judgment call on when brand identity should override platform idiom. Use this whenever building a mobile app screen, a React Native or Expo UI, or a layout that must work as a real touch interface — and whenever the user mentions iOS, Android, the App Store, tap targets, thumb reach, or mobile navigation."
---

# Mobile UI Conventions

A mobile interface is operated by a thumb, on glass, often in sunlight, by a user
whose muscle memory was trained by the platform — not by your app. Two failure modes
follow: a screen that ignores *ergonomics* is unusable in the hand, and one that
ignores *idiom* feels foreign in the ecosystem, forcing users to think about the
interface instead of their task. This skill owns both, plus the judgment call about
when breaking idiom is the right decision.

References: `references/apple-hig.md` (iOS idiom), `references/md3.md` (Android /
Material 3 idiom), `references/touch-ergonomics.md` (target sizes, thumb zones, and
field conditions — the numbers live there).

## First: which platform, which container

Establish before designing: iOS, Android, or both; native, React Native/Expo, or a
web view. Cross-platform does **not** mean identical — the shippable rule is:

> **Interaction grammar follows the platform. Identity travels.**

Navigation structure, back behavior, control idioms, type handling, and motion follow
each platform's reference. Brand — palette, illustration, voice, type flavor in
display roles — carries across unchanged. A React Native codebase can honor both from
one tree; "one design for both platforms" almost always means "iOS design worn
awkwardly by Android."

## Touch ergonomics — the part that makes or breaks field use

The numbers and their sources are in `references/touch-ergonomics.md`; the
non-negotiables:

- **Floors:** 44×44pt (iOS), 48×48dp (Android), with ≥8dp between adjacent targets.
  WCAG 2.2's 24px is a floor-of-floors, not a goal. For field conditions — gloves,
  sunlight, movement — primary actions go to 56dp+; a glove blurs the capacitive
  contact patch, so accuracy is bought with size and spacing, not user care.
- **Visual size and hit area are separate decisions.** A 24dp icon can carry a 48dp
  hit area (`hitSlop` in RN, padding elsewhere). Never let a small glyph mean a small
  target.
- **Design for the thumb's actual reach:** bottom third of the screen is the easy
  zone one-handed; top corners are the hardest. Frequent actions live at the bottom;
  destructive actions live *outside* the natural sweep and never adjacent to
  frequent ones — the cost of a miss is asymmetric, so the layout must be too.
- **Forgiveness over confirmation** in the field: undo beats "are you sure?" dialogs,
  drafts autosave on interruption (phone calls and dead batteries are normal
  jobsite events), and critical actions debounce against wet-screen phantom touches.

## Safe areas and insets

Content and controls respect the safe area on every edge: status bar / Dynamic
Island / punch-hole at the top, home indicator and gesture bar at the bottom,
landscape "ears." Never hardcode inset values — read them (`useSafeAreaInsets` in RN)
because they differ per device and orientation. The keyboard is an inset too: the
focused field is never occluded, scroll-into-view on focus, and the submit action
stays reachable while the keyboard is up. A bottom action bar that the home-indicator
gesture area overlaps is the most common safe-area bug in RN apps.

## Navigation grammar and gesture conflicts

Each platform's grammar is in its reference; the cross-platform rules:

- **Bottom navigation (3–5 destinations) is the shared safe pattern** — it satisfies
  the iOS tab bar and the MD3 navigation bar with per-platform styling. Hamburger
  drawers are a last resort on both platforms now.
- **System back is sacred on Android.** Every screen answers the back gesture
  (predictive back included) sensibly; back is never trapped, repurposed, or ignored.
  On iOS the same reverence goes to the left-edge back swipe.
- **Gesture conflicts are design bugs, not polish items.** Horizontal carousels near
  screen edges fight the iOS back swipe and Android gesture nav; swipe-to-delete
  fights page swipes. Detect the collision at design time and give one gesture up.
- **Every gesture has a visible alternative.** Nothing important lives behind
  long-press-only, multi-finger, or an undiscoverable swipe — gestures are
  accelerators, not the only door. (Gloves also defeat long-press reliably.)

## Type and dynamic sizing

System type stacks by default — SF on iOS, Roboto/system on Android — which buys
correct rendering, Dynamic Type/font-scale support, and platform feel for free; brand
display faces appear in heading roles only (the pairing itself is `frontend-design`'s
call). The hard rule is scaling: users *will* run 130%+ text scale, so layouts must
survive it — text in `sp` on Android (never `dp`), Dynamic Type styles on iOS, no
fixed-height text containers, and test at the largest supported size. Body text
floors: ~17pt iOS / 16sp Android.

## Motion

Follow the platform's motion language (springs and sheets on iOS; MD3's emphasized
easing, container transform, and predictive-back previews on Android), keep durations
inside platform norms, and respect the reduce-motion setting both platforms expose —
it's an accessibility contract, not a preference.

## The override judgment — when brand may beat platform

This skill's core judgment call. The default split: **platform wins interaction
grammar; brand wins identity.** Muscle memory is the user's asset — spending it to
look different is almost always a bad trade. Override platform idiom only when one of
these genuinely holds:

1. **The domain pattern is stronger than the platform pattern** — a camera-first
   capture flow, a map-first dispatch screen: the work's shape beats the widget
   catalog.
2. **A mixed-device workforce needs one trained flow** — when the same field crew
   shares iPhones and Androids and training cost dominates, converging on one
   grammar (documented) can beat per-platform familiarity.
3. **Field or accessibility constraints exceed platform minimums** — glove targets
   above MD3 sizing, sunlight contrast above either platform's palette comfort.

An override is a design decision: record it with its reason (the DESIGN ledger via
`design-workflow`/`project-artifacts`, where installed) so it survives as a choice
rather than reading as ignorance of the convention it broke.

**Never override, under any brand pressure:** system back behavior, safe-area
respect, text scaling, or the platform's accessibility services (VoiceOver,
TalkBack). These aren't idiom; they're the floor.

## Boundaries

- **Aesthetic direction** — palette, type pairing, signature element — belongs to
  `frontend-design`, where installed. This skill constrains those choices for touch
  and platform; it never makes them.
- **The workflow around UI work** — ledger, mockup-as-spec, review — belongs to
  `design-workflow`, where installed; this skill is consulted inside that sequence
  when the surface is mobile.
- **3D inside a mobile app** → `webgl-budget`, where installed; its mobile
  performance budget governs, not this skill.
- **Proving it works on a real device** — including performance under throttling —
  is `verification-discipline`'s bar, where installed. "Looks right in the simulator"
  is not a field test.
