# Default Skin — Element IDs Reference

Source: `web/skins/default/meter.svg` (default skin element ids)

Use this list when naming groups/paths in the **official** skin. Each element
id maps to the semantic keys in `skin.json` (`digit_prefix`, `unit`, `prefix`,
`icons`, etc.). If the official skin uses different ids, update its own
`skin.json` to match — the code only cares that `skin.json` ids exist in the
skin's `meter.svg`.

## Digits (5 cells × 7 segments + dp = 40 ids)

| | a | b | c | d | e | f | g | dp |
|---|---|---|---|---|---|---|---|---|
| digit0 | `digit0_a` | `digit0_b` | `digit0_c` | `digit0_d` | `digit0_e` | `digit0_f` | `digit0_g` | `digit0_dp` |
| digit1 | `digit1_a` | `digit1_b` | `digit1_c` | `digit1_d` | `digit1_e` | `digit1_f` | `digit1_g` | `digit1_dp` |
| digit2 | `digit2_a` | `digit2_b` | `digit2_c` | `digit2_d` | `digit2_e` | `digit2_f` | `digit2_g` | `digit2_dp` |
| digit3 | `digit3_a` | `digit3_b` | `digit3_c` | `digit3_d` | `digit3_e` | `digit3_f` | `digit3_g` | `digit3_dp` |
| digit4 | `digit4_a` | `digit4_b` | `digit4_c` | `digit4_d` | `digit4_e` | `digit4_f` | `digit4_g` | `digit4_dp` |

Segment layout:

```
     aaaa
    f    b
    f    b
     gggg
    e    c
    e    c
     dddd        (dp)
```

## Static / labels

- `glass` — LCD glass background
- `fn_text` — function label (e.g. `DCV`), text is set at runtime
- `rtc_text` — RTC timestamp label, text is set at runtime

## Sign

- `sign_neg` — negative sign (minus)

## Prefixes (6)

`prefix_n`, `prefix_mu` (µ), `prefix_m`, `prefix_k`, `prefix_M`, `prefix_G`

## Units (7)

`unit_v`, `unit_a`, `unit_ohm` (Ω), `unit_hz`, `unit_pct` (%), `unit_degc` (°C), `unit_degf` (°F)

## Icons / annunciators (10)

`icon_hold`, `icon_rel`, `icon_auto`, `icon_ahold`, `icon_crest`, `icon_rec`, `icon_max`, `icon_min`, `icon_avg`, `icon_battery_low`

---

## Inkscape-internal ids (ignore — not used by the skin)

`svg1` (root), `defs1`, `namedview1` — Inkscape bookkeeping; the overlay
already skips the root id when injecting.

## Rules

- ids must be **unique** in the SVG
- use lowercase `[a-z0-9_]` (no spaces, no leading digits)
- every id in `skin.json` must exist in `meter.svg`
