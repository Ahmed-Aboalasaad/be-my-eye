# Design System: Be My Eye

## 0. Context Deviation Notice

This app is a voice-first accessibility tool for blind and low-vision users, not a marketing site or dashboard. Several standard "anti-slop" rules from general design taste are **intentionally inverted** here, because the opposite choice is what accessibility demands:

- **Centered, single-target layout is correct, not banned.** There is one screen and one giant full-bleed gesture target. A blind user cannot scan an asymmetric grid — predictability and centering are the accessible choice.
- **No hero section, no CTA copy, no marketing language.** There is nothing to sell and no scroll. The "content" is the live state text.
- **Motion is functional, not decorative.** A gentle pulse during "Listening" is haptic-adjacent feedback (paired with real device haptics), not a perpetual micro-interaction for visual delight. No motion competes with or distracts from the screen reader's announcement.
- **Color never carries meaning alone.** Every state is communicated redundantly through text, a semantics label (screen reader), and haptics — color is a bonus for sighted/low-vision users and helpers, never the sole signal.

Everything else — palette discipline, typography quality, banned AI clichés — applies as normal.

## 1. Visual Theme & Atmosphere

Calm, high-contrast, unhurried. Density 2/10 (one screen, one purpose). Variance 2/10 (deliberately predictable — this is the one place symmetry is correct). Motion 3/10 (a single slow, functional pulse during Listening; otherwise static). The atmosphere is a quiet, confident instrument panel with exactly one control — closer to a calm intercom than an app.

## 2. Color Palette & Roles

- **Canvas Ink** (#12141A) — Primary background (dark by default; avoids glare, better battery, calmer for a screen most users won't be visually reading anyway). Not pure black.
- **Surface Panel** (#1C1F27) — The single full-bleed gesture container's resting surface.
- **Warm Paper** (#F5F3EE) — Primary text on dark surfaces (soft off-white, not stark #FFFFFF, reduces harsh contrast flicker for low-vision users).
- **Muted Fog** (#8B90A0) — Secondary/idle-state text.
- **Signal Amber** (#E8A33D) — Single accent. Used only for the "Listening" pulse ring and the recording indicator. Saturation kept below 80%; warm rather than neon.
- **Alert Coral** (#E5674B) — Reserved solely for error state text/border. Never used decoratively.

Max one accent (Signal Amber) plus one reserved semantic color (Alert Coral) for errors only — errors are a distinct communicative category, not a second "accent," so this does not violate the one-accent rule in spirit.

## 3. Typography Rules

- **Display/State text:** `Outfit` — the one large line of state text (`Hold to ask`, `Listening…`, the answer). Weight-driven hierarchy, not size-screaming. Track-normal (not tight — tight tracking hurts low-vision legibility).
- **Body/secondary:** `Outfit` at a lighter weight for any secondary caption.
- **Mono:** not applicable — no numeric/tabular data on this screen.
- **Minimum size:** display text never below 28px (this screen is read from a distance / by low-vision users, well above the general 14px body-text floor).
- **Banned:** `Inter` (per standard taste rules), any serif (this is a utility screen, not editorial).

## 4. Component Stylings

- **The screen is one component:** a full-bleed `Semantics`-labeled pressable surface. No buttons, no icons required for the core interaction (the entire screen *is* the button).
- **Press feedback:** on press-and-hold, the surface tints toward Signal Amber at low opacity (~12%) and a soft pulse ring animates outward from center at spring physics (stiffness 100, damping 20) — functional recording feedback, paired with a haptic tick at press-start.
- **State text transitions:** crossfade only (200ms opacity), never slide/scale — abrupt position changes are disorienting for low-vision users tracking with partial focus.
- **No cards, no shadows, no borders** — nothing to visually parse; the whole screen is the surface.
- **Error state:** text recolors to Alert Coral, screen reader announces "Error: …" — no modal, no dismiss button (next press-and-hold simply retries).

## 5. Layout Principles

- Single full-bleed container, safe-area aware, centered text with generous padding (min 24px, scaling up on tablets).
- No responsive breakpoints beyond safe-area insets — this is a phone-held-in-hand tool, not a multi-column layout.
- Touch target is the entire screen (trivially exceeds the 44px minimum).

## 6. Motion & Interaction

- Exactly one animated element: the Listening pulse ring, spring physics, `transform`/`opacity` only.
- No staggered reveals, no scroll-triggered animation (there is no scroll).
- Haptic tick on press-start and on response-ready, in addition to the visual/audio cues — redundant signaling across modalities is the core accessibility principle here, not decoration.

## 7. Anti-Patterns (Banned)

No emojis. No `Inter`. No generic serif. No pure black (`#000000` — use Canvas Ink `#12141A`). No neon/outer glow. No AI copywriting clichés. No decorative motion unrelated to actual state. No relying on color alone to convey any state (every color change is paired with a text and semantics-label change). No hero section, no CTA button copy, no marketing language — this screen has no audience to persuade, only a user to serve.
