---
name: AGNIYA
description: Analytics on encrypted bank data, presented as a green-bar clearing printout.
colors:
  paper: "#f3f5ef"
  sheet: "#f7f9f4"
  slip: "#fbfcf8"
  band: "#dfecda"
  band-line: "#c3d8bd"
  input-line: "#9fb79a"
  ink: "#1b1f1d"
  ink-faded: "#4f5a53"
  checked-green: "#1f6b48"
  ribbon-red: "#b92d19"
typography:
  display:
    fontFamily: "Archivo (wdth 125), system-ui, sans-serif"
    fontSize: "clamp(2.2rem, 3.7vw, 3.5rem)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Archivo (wdth 125), system-ui, sans-serif"
    fontSize: "clamp(1.7rem, 2.6vw, 2.4rem)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Archivo (wdth 112), system-ui, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.65
  figure:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "clamp(1.5rem, 2.4vw, 2.1rem)"
    fontWeight: 600
    letterSpacing: "-0.02em"
  tag:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "0.72rem"
    fontWeight: 400
  cipher:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "10px"
    lineHeight: "13px"
rounded:
  none: "0px"
spacing:
  gutter-mobile: "20px"
  gutter-desktop: "40px"
  section: "64px"
  section-lg: "80px"
components:
  button-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    height: "44px"
    padding: "0 20px"
  button-paper:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "44px"
    padding: "0 20px"
  step-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
  row-band:
    backgroundColor: "{colors.band}"
    textColor: "{colors.ink}"
---

# Design System: AGNIYA

## Overview

**Creative North Star: "The Clearing Printout"**

AGNIYA looks like the paper a bank's back office has always trusted: continuous fanfold stock with pale green bars, tractor-feed holes down both edges, perforated tear lines between sheets, and figures struck in ribbon-black. Every query result is printed like a clearing-house message: the query in monospace, the figure large, its conditions beside it, and a green "checked" stamp when the integrity tags match. Customer rows never appear on the paper; ciphertext does, as dense pixel-crisp hex drawn from real bytes.

The world is light by design: the dashboard is shown on a projector in a lit hall, where a pale sheet with black figures carries furthest. Density is a printed report's: generous margins, tight lines, figures in a right-hand column. The world refuses the encryption-startup default of dark navy, shields and glowing accents.

**Key Characteristics:**
- Paper, bands and ink; no gradients, no glass, no glow.
- Square corners everywhere.
- Two faces: Archivo expanded for headings, Martian Mono for figures, tags, queries and ciphertext.
- Colour carries state only: green for checked, red for failures, ink for everything else.
- Motion is paper feed: printed lines clip in left to right at a constant rate; new results slide down from the top.

## Colors

A restrained printout palette: pale green-grey stock, one band colour, ribbon-black ink, and two state inks.

### Primary
- **Ribbon Black** (#1b1f1d): all figures, headings and body text; the fill of primary buttons and the active step.

### Neutral
- **Fanfold Stock** (#f3f5ef): page ground behind the sheet.
- **Sheet** (#f7f9f4): the printed sheet and panels inside it.
- **Slip** (#fbfcf8): message slips (the live slip, the results roll), a step lighter than the sheet.
- **Green Bar** (#dfecda): alternate printed lines and rows.
- **Band Edge** (#c3d8bd): hairline rules, borders, perforations.
- **Form Rule** (#9fb79a): input and control borders, the drop-zone dash.
- **Faded Ribbon** (#4f5a53): secondary text, tags, conditions (6.4:1 on Fanfold Stock).

### State inks
- **Checked Green** (#1f6b48): the "checked" stamp, the encrypted stamp, the key-in-browser pill, focus rings.
- **Ribbon Red** (#b92d19): errors, tamper, a blocked bank question, the server-holds-the-key pill.

### Named Rules
**The Band Holds Whole Lines Rule.** A green bar always covers whole printed lines or whole rows, alternating by index (even rows banded). Never a background stripe that rows fall across.

**The Paper Is Territory Rule.** Bands and sheets mark where things are. State is carried only by ink (green or red), never by paper colour.

## Typography

**Display Font:** Archivo at width 125 (fallback system-ui)
**Body Font:** Archivo at normal width
**Label/Mono Font:** Martian Mono

**Character:** A wide report-header grotesque over a line-printer mono: headings read like a statement header, figures like a ledger column.

### Hierarchy
- **Display** (800, clamp(2.2rem, 3.7vw, 3.5rem), 1.02): the home page headline only.
- **Headline** (700, clamp(1.7rem, 2.6vw, 2.4rem), 1.08): section headings.
- **Title** (700, 1.05-1.15rem, width 112): step and panel titles.
- **Body** (400, 1.02-1.05rem, 1.65): explanations, at most 65-70ch.
- **Figure** (Martian Mono 600, 1.3-3.4rem): every measured or computed number; results on the dashboard run up to clamp(2.2rem, 4vw, 3.4rem) for the projector.
- **Tag** (Martian Mono 400, 0.72rem): message field tags such as ":61:" and ":32A:" on the home page.
- **Cipher** (Martian Mono, 10px / 13px): ciphertext hex only.

### Named Rules
**The Mono Means Data Rule.** Martian Mono is for figures, queries, tags and ciphertext. Prose never sets in mono.

**The Projector Floor Rule.** On the dashboard no text is smaller than 0.875rem.

## Layout

Content sits on a sheet inside a 1320px container. On desktop the sheet has 28px tractor strips with 5px holes on both edges; below 768px the strips are 16px with 3px holes. Sections inside the sheet are separated by perforation lines and use 20px side gutters on phones, 40px on desktop, and 64-80px vertical padding. Home sections vary the composition: hero split (copy left, live slip right), a five-cell route, a run report (copy left, figures right), a full-width comparison table, a banded listing, a two-column list, and a closing split. The dashboard is a four-step strip, then one column per step; step 3 puts bank questions and the query form in a 320-400px left column and the results roll on the right.

## Elevation & Depth

Flat by default: depth comes from paper layers (stock, sheet, slip) and rules, not shadows. One shadow exists: the live slip on the home page lifts off the sheet (`box-shadow: 0 18px 40px -24px rgba(27,31,29,0.45)`), as a slip laid on a printout. The sticky header is solid paper, never blurred.

## Shapes

All corners are square (0px), including buttons, inputs, steps and pills. Borders are 1px hairlines in Band Edge; emphasis rules are 2px Ribbon Black under table heads and around the limits strip. Perforations are 6px dashes with 5px gaps.

## Components

- **Ink button**: Ribbon Black fill, Fanfold Stock text, 44px high, 20px side padding, semibold; hover darkens slightly, press moves it down 1px. One per intent.
- **Paper button**: 1px ink border, transparent fill; hover fills with Green Bar.
- **Step strip**: four equal cells separated by 1px Band Edge; the active step fills with Ribbon Black.
- **Protection selector**: a row of four square segments (Plain, AES-256, Paillier, Paillier + range); the chosen one is ink-filled; Paillier options disable for text columns.
- **Result slip**: query line in mono, time and one-time setup on the right, the figure or a banded group table, a conditions line, and a stamp (green "Checked: integrity tags match", or faded "Decrypted by the server").
- **Stamp**: 2px border in its ink, mono uppercase 0.75rem.
- **Live slip** (home): header line, three synthetic rows with real Paillier ciphertext, product line, total and stamp, each on its own band; "Print again" re-encrypts with new randomness.

## Do's and Don'ts

- **Do** show the mechanism working (ciphertext, a key that never leaves, a check that passed) instead of adjectives.
- **Do** keep every figure traceable to `tools/bench_results.json`, the dashboard, or `docs/BANKING.md`, with its conditions printed beside it.
- **Do** use Ribbon Red only for something that failed or is unsafe.
- **Don't** add eyebrows or kicker labels above headings; field tags live inside slips and listings, not above headlines.
- **Don't** use same-size card grids as page structure; use banded listings, run reports or the route grid.
- **Don't** round corners, blur surfaces, or add gradients or glows.
- **Don't** add a dark theme without a new use scene; the light sheet is a projector decision.
