Workspace rules: ~/Documents/workspace/CLAUDE.md

# color_harmony — rules for agents

Workspace rules apply; this file adds the project's own. **Reply to Alexey in Russian**, in product terms.
Agent files in English; DECISIONS, ROADMAP, ITERATIONS, experiment reports are Russian (they are for Alexey).

## What this is

A non-commercial, Apple-native photo editor built on "harmonic colour thinking" (working name: **Accordion**, set by Alexey 2026-10-13; workspace tag/folder stay `color_harmony`).
Colour is edited through relations between colours, not presets or neural filters: neutrals are hard reference
points, skin is a soft one, complementary pairs and chords rotate together on a colour wheel, the tool explains itself.
Today: a browser prototype «Комплементарный круг» (`prototype/complement.html`, published as a claude.ai artifact) and a
measurement pipeline (`tools/film_measure/`) that tests what film, scanners and cameras do to colour.
Next: a transferable colour «recipe» (a film/scanner "school" as hue-dependent rotation + chroma gain), then Swift/Metal.

## Start of a session

1. `git log --oneline -20`; then `ws:30_agents/color_harmony.md` (`grep -n` your name and «всем», `tail -60`).
2. `docs/NEXT_SESSION.md`, then your iteration in `ITERATIONS.md`; headings of `DECISIONS.md`, `ROADMAP.md`. Read only the section you need.

## Documents

| File | What | How to edit |
|---|---|---|
| `DECISIONS.md` | What Alexey decided, in his words, and why | Append only; literal, don't extend (ws rule 26) |
| `ROADMAP.md` | Phases, open questions | Keep current |
| `ITERATIONS.md` | Iterations → steps → «Итог» | Plan with Alexey; threads add «Итог» |
| `docs/NEXT_SESSION.md` | State for a new session, ≤ ~100 lines | Rewrite at each step end |
| `docs/data_sources.md` | Where data came from, rights, what is in git | Update when data changes |
| `docs/experiments/` | Measured results, one topic per file | Rewrite when a measurement overturns it (rule 27) |

## Code

- Prototype source of truth: `prototype/complement.html` (one file, vanilla JS, no deps). Build: `python3 prototype/build.py` →
  `prototype/build/` (ignored). Syntax check: extract the last `<script>` and `node --check`. Tests (Playwright):
  `cd prototype/build && node ../tests/fold.js` (hue/chroma monotonicity; must print 0 folds), `zoom_and_fold.js`, `reset_all.js`,
  `undo_and_table.js`, `curves.js` (curve tool; `OLD=<old complement_built.html>` for the byte check, `BREAK=1` must fail), `hsl.js` (plate «Цвета»: skin/neutral cores, samples, .cube vs render, UI, lips measurement; `BREAK=1` must fail). Needs `npm i playwright` (+ a browser; set `CHROMIUM=<path>` to use an installed one). On the author's machine (2026-10-14): `npm i playwright` in a scratch dir + `NODE_PATH=<dir>/node_modules`, `CHROMIUM=~/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`; last run 2026-10-14, 0 folds.
- Published artifact: https://claude.ai/artifact/AQtb8gA5SjqhnVht8qwod5 (v5, 2026-10-13). Publish `prototype/build/complement_built.html`
  to the same URL with capabilities `{"downloads":{}}`. Source stays here (ws rule 24).
- бета: https://claude.ai/artifact/MHjfLcC7MEtQHCujKBV7q8 («Accordion beta», 2026-10-14, v4: plate «Цвета» (HSL by 8 sectors with samples) on the v3 desktop shell; same build, publish to this URL for beta work, capabilities `{"downloads":{}}`).
- Measurements: `tools/film_measure/README.md`.

## Rules specific to this project

- **Numbers before conclusions.** A colour claim needs a measurement and its caveat. Colour numbers: Lab D50, CIEDE2000.
- **Data stays out of git**: scans are third-party (rights unknown), the demo photo shows a person. Only measured tables go in
  `data/derived/`. The repo may become public (ws rule 28) — assume it is.
- **Work in small tasks, compress between them.** One step = one task (≈ ≤10 tool calls or one long run). After a long run, write the result into `docs/NEXT_SESSION.md`, commit, and tell Alexey to start a fresh session (or `/compact`) before the next step. Don't chain several long runs in one session (limits).
- **Pins never fold hues** (`prototype/tests/fold.js` is the guard). Don't touch the hue-map maths without running it.
- Gamut mapping, LUT export (.cube in a stored ZIP — the `downloads` capability allows only zip), history/undo: don't rewrite unasked.
- Remote: https://github.com/alexeynovopashin-lab/accordion (public). Push/publish only after Alexey says so (record it in `INDEX.md`).
