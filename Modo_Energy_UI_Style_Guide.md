# Modo Energy UI Style Guide

A reference for building internal tools that feel like Modo Energy products.
Covers colors, typography, component patterns, and layout principles used in the Weekly Dispatch builder.

---

## 1. Color Palette

### Brand Purple (Primary)
| Token | Hex | Usage |
|-------|-----|-------|
| Purple | `#705FE6` | Primary buttons, active states, links, accent borders |
| Purple Dark | `#4E42A1` | Button hover states, pressed states |
| Purple Light | `#ECEAFA` | Selected card backgrounds, subtle highlights |
| Purple Glow | `rgba(112, 95, 230, 0.15)` | Focus rings, input focus shadows |
| Purple Shadow | `rgba(112, 95, 230, 0.25)` | Elevated purple element shadows |

### Dark Mode (Sidebar & Login)
| Token | Hex | Usage |
|-------|-----|-------|
| Dark BG | `#0A0F19` | Sidebar background, login page background |
| Elevated | `#161D2E` | Cards on dark backgrounds (login card, elevated panels) |
| Dark Text | `#D3D8E9` | Body text on dark backgrounds |
| Dark Border | `rgba(255, 255, 255, 0.06)` | Subtle dividers on dark surfaces |
| Dark Hover | `rgba(255, 255, 255, 0.04)` | Hover state on dark backgrounds |

### Light Mode (Main Content)
| Token | Hex | Usage |
|-------|-----|-------|
| Page BG | `#F8F8FB` | Main content area background |
| Panel BG | `#FFFFFF` | Cards, panels, form fields |
| Border | `#EAEAF2` | Default borders, dividers |
| Border Hover | `#CDCDDE` | Hovered borders |

### Text
| Token | Hex | Usage |
|-------|-----|-------|
| Primary Text | `#1A1A1A` | Headings, body text, labels |
| Secondary | `#4C4C71` | Subheadings, toolbar labels |
| Muted | `#8C8CAA` | Descriptions, hints, metadata, timestamps |

### Semantic
| Token | Hex | Usage |
|-------|-----|-------|
| Success | `#27AE60` | Completed states, confirmation |
| Danger | `#E84365` | Errors, destructive actions, delete buttons |
| Warning | `#F2994A` | Stale indicators, caution states |
| Info | `#2F80ED` | Informational badges |

---

## 2. Typography

**Font:** DM Sans (Google Fonts) -- used for everything. No secondary font.

```
https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap
```

### Scale

| Element | Size | Weight | Extras |
|---------|------|--------|--------|
| Page heading (h2) | 22px | 600 | `letter-spacing: -0.01em` |
| Section heading (h3) | 16px | 600 | -- |
| Body text | 14px | 400 | `line-height: 1.6` |
| Buttons | 13px | 600 | `letter-spacing: 0.2px` |
| Labels / metadata | 13px | 500 | color: `#4C4C71` |
| Small / captions | 11-12px | 500-600 | Often uppercase with `letter-spacing: 1.5px` |
| Brand wordmark | 13px | 700 | `letter-spacing: 6px`, uppercase |

### Text rendering
```css
-webkit-font-smoothing: antialiased;
```

---

## 3. Spacing & Layout

### Core Values
- **Border radius (small):** 4px -- buttons, inputs, cards
- **Border radius (large):** 8px -- panels, modals, region cards
- **Border radius (circle):** 50% -- step indicators, status dots
- **Sidebar width:** 260px
- **Panel max-width:** 640px (keeps reading line length comfortable)
- **Content padding:** 40px vertical, 48px horizontal

### Shadows
| Level | Value | Usage |
|-------|-------|-------|
| Subtle | `0 1px 3px rgba(18,18,43,0.12)` | Default cards, buttons |
| Medium | `0 4px 14px rgba(18,18,43,0.14)` | Hovered cards, dropdowns |
| Large | `0 8px 24px rgba(18,18,43,0.12)` | Modals, floating panels |
| Purple | `0 4px 14px rgba(112,95,230,0.25)` | Primary buttons, selected cards |

### Transitions
- Fast (hover, focus): `150ms ease`
- Base (panel switches, color changes): `200ms ease`

---

## 4. Component Patterns

### Buttons

Four tiers of visual weight, used to create clear action hierarchy:

**Primary** -- filled purple. The single most important action on screen.
```css
background: #705FE6;
color: #fff;
border: 1px solid #705FE6;
box-shadow: 0 1px 3px rgba(112,95,230,0.3);
/* Hover: background darkens to #4E42A1, shadow grows */
```

**Secondary** -- outlined purple. Important but not the main CTA (Fetch, Generate).
```css
background: transparent;
color: #705FE6;
border: 1px solid #705FE6;
/* Hover: background fills with #ECEAFA */
```

**Default** -- white with gray border. Neutral actions.
```css
background: #fff;
color: #1a1a1a;
border: 1px solid #EAEAF2;
/* Hover: border darkens, subtle lift (translateY -1px) */
```

**Ghost** -- no border, no background. Low-priority actions (Skip, Log Out).
```css
background: transparent;
border-color: transparent;
color: #8C8CAA;
/* Hover: text turns purple, underline appears */
```

**Destructive ghost** -- same as ghost but in faded red. For Reset, Delete.
```css
color: rgba(232,67,101,0.6);
/* Hover: full red #E84365, underline */
```

### Selectable Cards

Cards that users click to choose items (articles, subject lines, podcasts):
- Default: white background, `#EAEAF2` border
- Hover: border darkens to `#CDCDDE`, subtle shadow appears
- Selected: purple border, `#ECEAFA` background, purple outer glow (`box-shadow: 0 0 0 1px #705FE6`)
- Checkbox indicator fills purple with white checkmark on select

### Form Inputs

- White background, `#EAEAF2` border, 4px radius
- Focus: border turns purple, 3px purple glow ring (`box-shadow: 0 0 0 3px rgba(112,95,230,0.15)`)
- Labels: 13px, weight 500, color `#4C4C71`, 6px below margin
- Textareas: minimum height 80px, vertical resize only

### Toast Notifications

Slide in from the right, dark background (`#0A0F19`):
- Success: 3px left border in green (`#27AE60`)
- Error: 3px left border in red (`#E84365`)
- Auto-dismiss with fade-out animation

---

## 5. Layout Patterns

### Dark Sidebar + Light Content

The app uses a split layout:
- **Left sidebar** (260px): dark background (`#0A0F19`) with light text, contains navigation and branding
- **Main area**: light background (`#F8F8FB`) with white content panels

This creates strong visual separation between navigation and workspace.

### Sidebar Navigation (Step Wizard)

Each step is a button with:
- Circular step number (24px, `border-radius: 50%`)
- Default: dim circle (`rgba(255,255,255,0.08)` background)
- Active: purple background on the number, purple left border bar (3px, animated with `scaleY`)
- Completed: green circle with white checkmark (number replaced via CSS `font-size: 0` + `::after` pseudo-element)

### Sidebar Footer

Three-row footer at the bottom:
1. Action buttons (Save Progress, Reset, Log Out) in a flex row
2. "Internal Tool" label -- ultra-small (10px), uppercase, very dim (`rgba(255,255,255,0.25)`)

### Confirm Bar

Sticky bar at the bottom of scrollable content:
- White background, subtle top shadow for scroll-behind effect
- 2px purple left accent border
- Shows selection count on the left, confirm button on the right

---

## 6. Login Page

Full-screen dark background matching the sidebar color. Centered card:
- Card: `#161D2E` background, 12px radius, generous padding (48px 40px)
- "MODO ENERGY" in purple, uppercase, 14px, `letter-spacing: 0.08em`
- Title in white, subtitle in muted gray
- Inputs: dark background (`#0A0F19`), subtle border (`#2A3348`), focus ring in purple
- Submit button: full-width purple
- Error state: red tinted background with red border, slides in on bad credentials
- "Internal tool" footer in very dim text

---

## 7. Design Principles

### 1. Purple is the accent, not the base
Purple appears in focused moments -- active buttons, selected cards, focus rings, the sidebar active indicator. The majority of the UI is neutral grays and whites. This makes purple feel intentional rather than overwhelming.

### 2. Hierarchy through weight, not color
Buttons use four visual tiers (filled, outlined, default, ghost) to signal importance. The most important action on any screen should be the only primary (filled purple) button. Everything else steps down in weight.

### 3. Dark for chrome, light for content
The sidebar and login page use the dark palette because they're navigation/chrome. The working area where users read and edit content uses light backgrounds for readability. This split is consistent across all views.

### 4. Subtle motion, not animation
Hover lifts are 1-2px (`translateY(-1px)`). Transitions are 150-200ms. The loading spinner is the only looping animation. Everything else is a single state change. No bounces, no slides, no attention-seeking motion.

### 5. No emojis, no icons (mostly)
Buttons use text labels only. The only graphical elements are the checkmark in completed steps (CSS-generated) and the status dot in the preview header. This keeps the interface professional and lets the typography carry the hierarchy.

### 6. Consistent focus states
Every interactive element gets the same purple glow ring on focus: `box-shadow: 0 0 0 3px rgba(112,95,230,0.15)`. This is an accessibility requirement and a brand signature.

### 7. Empty states guide the user
When a list has no content, a dashed-border placeholder appears with instructional text ("Click a button above to load items"). This prevents blank, confusing screens.

---

## 8. Quick-Start CSS Variables

Copy this block into any new project to get the Modo Energy look immediately:

```css
:root {
    --purple: #705FE6;
    --purple-dark: #4E42A1;
    --purple-light: #ECEAFA;
    --purple-glow: rgba(112, 95, 230, 0.15);

    --bg: #F8F8FB;
    --bg-dark: #0A0F19;
    --bg-elevated: #161D2E;
    --panel-bg: #ffffff;

    --text: #1a1a1a;
    --text-muted: #8C8CAA;
    --text-secondary: #4C4C71;

    --border: #EAEAF2;
    --border-hover: #CDCDDE;

    --danger: #E84365;
    --success: #27AE60;
    --warning: #F2994A;

    --radius: 4px;
    --radius-lg: 8px;
    --shadow: 0 1px 3px rgba(18,18,43,0.12);
    --shadow-md: 0 4px 14px rgba(18,18,43,0.14);

    --font: 'DM Sans', sans-serif;
}
```

---

*This guide documents the design system as built for the Weekly Dispatch newsletter tool. It can be applied to any internal Modo Energy web tool to maintain visual consistency.*
