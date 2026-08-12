# Authoring an overlay skin

A skin is a folder under `web/skins/<name>/`:

```
web/skins/<name>/
├── skin.json     # declarative config (required)
├── meter.svg     # your artwork; element ids must match skin.json (required)
├── skin.js       # optional — only if you need custom rendering
└── skin.css      # optional stylesheet
```

Open it with `http://<host>:<port>/?skin=<name>` (add `&debug=1` while developing).

There are **two ways** to build a skin:

## 1. Declarative LCD skin (no JS needed)

For LCD-style 7-segment meter displays, set `"renderer": "lcd"` (or simply omit
`skin.js`) — the host's built-in renderer drives digits, sign, units, prefixes,
icons, battery and function icons purely from `skin.json`:

```json
{
  "name": "myskin",
  "digits": 5,
  "digit_prefix": "digit",
  "no_dp": [4],
  "sign": "sign_neg",
  "unit": { "V": "unit_v", "A": "unit_a", "Ω": "unit_ohm", "%": "unit_pct" },
  "prefix": {
    "V": { "m": "prefix_m", "k": "prefix_k", "M": "prefix_M" },
    "A": { "m": "prefix_m", "k": "prefix_k" }
  },
  "icons": { "hold": "icon_hold", "min": "icon_min" },
  "battery_low": "icon_bat",
  "function": {
    "type": "icons",
    "map": { "DCV": "icon_dc", "ACV": "icon_ac" }
  },
  "right_aligned": ["Duty Cycle (%)"]
}
```

`skin.js` is **optional**: if a skin has no working render module, the host
falls back to this same built-in renderer automatically, so the minimum viable
skin is `skin.json` + `meter.svg`.

## 2. Custom render (skin.js)

Write `skin.js` that registers a module:

```js
window.__bm_skins = window.__bm_skins || {};
window.__bm_skins.myskin = {
  name: 'myskin',
  render(state, ctx) { /* paint using ctx helpers */ },
};
```

`render(state, ctx)` is called every ~200 ms with a **semantic** state —
no protocol knowledge needed:

| state field     | meaning                                        |
|-----------------|------------------------------------------------|
| `mode`          | `'idle' | 'numeric' | 'ascii' | 'overload' | 'all'` |
| `value_digits`  | cells `{char, segments[], dp}` for the display |
| `sign`          | negative reading?                              |
| `unit` / `prefix` | e.g. `'V'` / `'m'`                           |
| `function`      | canonical SDK function name (e.g. `'DCV'`)     |
| `icons`         | `{hold, relative, auto, auto_hold, crest, record, max, min, avg}` |
| `battery_low`   | battery icon on?                               |
| `rtc`           | timestamp string (if the skin shows it)        |

`ctx` paint helpers: `byId(id)`, `show(id, on)`, `lightDigits(cells, offset)`
(offset 0 = left-align, `skin.digits - cells.length` = right-align),
`lightSign(on)`, `lightUnits(unit)`, `lightPrefixes(unit, prefix)`,
`lightIcons(icons)`, `lightBattery(low)`, `lightAllUnits/Prefixes/Icons`.
`ctx.skin` is your parsed `skin.json`. Handle `state.mode === 'all'` as a
self-test that lights every element you own.

## skin.json reference

| key              | type            | notes |
|------------------|-----------------|-------|
| `name`           | string          | required; should match the folder name |
| `digits`         | int             | required; number of 7-seg digits |
| `digit_prefix`   | string          | required; segment ids are `<prefix><d>_<seg>` |
| `no_dp`          | int[]           | digit indexes with **no** decimal-point element (e.g. `[4]`) |
| `script`         | string          | render module filename (default `skin.js`) |
| `renderer`       | `"lcd"`         | use the built-in renderer instead of a script file |
| `sign`           | string          | negative-sign element id |
| `unit`           | map             | unit → element id (see `state.unit` values) |
| `prefix`         | map of maps     | unit → prefix → element id |
| `icons`          | map             | annunciator key → element id |
| `battery_low`    | string          | battery element id |
| `hidden`         | string[]        | element ids the skin owns but never drives |
| `function.type`  | `"icons" \| "text"` | how the function is shown |
| `function.map`   | map             | (`icons`) function name → id or `[ids]`; shared ids light for every function that lists them |
| `function.id`    | string          | (`text`) element id whose textContent shows the function name |
| `function_labels`| map             | (`text`) display override per function name; missing names fall back to canonical |
| `rtc_label`      | string          | element id whose textContent shows the timestamp |
| `right_aligned`  | string[]        | function names whose reading is right-aligned (built-in LCD renderer only) |

Element ids **must** exist in `meter.svg`, be unique, and use lowercase
`[a-z0-9_]`. See `docs/skin-element-ids.md` for the default-skin id catalog.

## Development loop

- `python demo.py --port 8765` serves a menu of every function (and special
  states incl. "ALL (light everything)") — no meter needed.
- Add `&debug=1` to the overlay URL: skin `render()` errors that the poll loop
  would otherwise swallow are printed to the console **and** shown in a red
  strip at the bottom of the page. This is the fastest way to catch a bug that
  "just doesn't display".
- While `debug=1`, skin scripts are re-fetched with a cache-buster on every
  page load, so a normal refresh picks up edits.

## Validating a skin

```bash
.venv\Scripts\python tools\check_skin.py            # all skins
.venv\Scripts\python tools\check_skin.py myskin     # one skin
```

The validator checks: `skin.json` parses, every referenced id exists in
`meter.svg`, ids are unique, `function.map` / `right_aligned` names are real
SDK functions, and warns on SVG ids never referenced and SDK functions the
icon map doesn't cover. It exits non-zero if any skin has errors — wire it into
a pre-commit hook or CI if you like.
