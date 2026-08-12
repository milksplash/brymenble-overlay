/* Default skin render module.
 *
 * New base design (meter.svg): a black panel with
 *   text_reading  — the large reading (right-aligned to the right margin)
 *   text_function — the function label (authored right-anchored)
 * plus the small status-annunciator text icons (Hold/Rel/Auto/A-Hold/Crest/
 * Rec/Max/Min/Avg/Bat) routed from state.icons / state.battery_low via
 * skin.json "icons" / "battery_low". No 7-seg bars, unit/prefix glyphs or
 * RTC elements yet; the SVG is still being iterated on.
 *
 * Register: window.__bm_skins['default'] = { render(state, ctx) {...} }.
 */
window.__bm_skins = window.__bm_skins || {};
window.__bm_skins['default'] = (function () {
  const READING_ID = 'text_reading';
  const FUNCTION_ID = 'text_function';
  // Right edge of the reading, in meter.svg group coordinates — set to the
  // same x as text_function so the reading shares its right margin.
  const RIGHT_X = 168.02924;

  // Functions whose range unit (with prefix) is shown in the function text —
  // e.g. Resistance reads "MΩ"/"kΩ", Capacitance "µF", Hz of Line Signal "Hz".
  const FUNCTIONS_WITH_PREFIX = new Set(['Resistance', 'Capacitance', 'Hz of Line Signal']);
  // Logic-Hz is special: the function text is the function label + prefixed
  // unit, e.g. "Logic kHz".
  const LOGIC_HZ = 'Logic-Hz';
  // Temperature functions show their unit (°C/°F) behind the function label —
  // e.g. "T1 °C", "T2 °F", "T1-T2 °C".
  const TEMP_FUNCTIONS = new Set(['T1', 'T2', 'T1-T2']);

  // Build the display string from the semantic cells: blanks for empty cells
  // and '.' after the cell that carries the decimal point.
  function valueText(state) {
    const cells = state.value_digits || [];
    let s = '';
    for (const c of cells) {
      s += c.char || ' ';
      if (c.dp) s += '.';
    }
    return s;
  }

  // Strip leading zeros from a numeric reading (e.g. "002.50" -> "2.50",
  // "000.25" -> "0.25") while keeping the ones-place digit before the dot.
  function stripLeadingZeros(s) {
    let i = 0;
    while (i < s.length && s[i] === '0') i++;
    let out = s.slice(i);
    if (out === '') out = '0';
    else if (out[0] === '.') out = '0' + out;
    return out;
  }

  // Range unit label with its prefix, from skin.json "unit_labels"
  // (key "<prefix>|<unit>", e.g. "M|Ω" -> "MΩ"; falls back to the bare unit).
  function unitLabel(state, skin) {
    const labels = skin.unit_labels || {};
    const key = `${state.prefix || ''}|${state.unit || ''}`;
    return key in labels ? labels[key] : (state.unit || '');
  }

  // "Light all" self-test (state.mode == "all"): every text field the skin
  // owns shows a representative content.
  function lightAll(ctx) {
    const r = ctx.byId(READING_ID);
    if (r) {
      r.textContent = '88888';
      r.setAttribute('text-anchor', 'end');
      r.setAttribute('x', RIGHT_X);
    }
    ctx.lightAllIcons();
    if (ctx.skin.battery_low) ctx.show(ctx.skin.battery_low, true);
    const fn = ctx.skin.function;
    if (fn && fn.type === 'text' && fn.id) {
      const f = ctx.byId(fn.id);
      if (f) f.textContent = 'ALL';
    }
  }

  return {
    name: 'default',
    render(state, ctx) {
      if (state.mode === 'all') {
        lightAll(ctx);
        return;
      }

      // Reading — right-aligned to the same right edge as text_function.
      const r = ctx.byId(READING_ID);
      if (r) {
        let text = valueText(state);
        if (state.mode === 'numeric') text = stripLeadingZeros(text);
        if (state.sign) text = '-' + text;
        r.textContent = text;
        r.setAttribute('text-anchor', 'end');
        r.setAttribute('x', RIGHT_X);
      }

      // Function label as text. Resistance/Capacitance/Hz of Line Signal also
      // show the range unit, so the prefix is included ("MΩ", "µF", "Hz").
      // Logic-Hz and the temperature functions (T1/T2/T1-T2) append the unit
      // behind the label ("Logic kHz", "T1 °C", "T1-T2 °F").
      const fn = ctx.skin.function;
      if (fn && fn.type === 'text' && fn.id) {
        const f = ctx.byId(fn.id);
        if (f) {
          const labels = ctx.skin.function_labels || {};
          let text = labels[state.function] || state.function || '';
          if (FUNCTIONS_WITH_PREFIX.has(state.function)) {
            text = unitLabel(state, ctx.skin) || text;
          } else if (state.function === LOGIC_HZ || TEMP_FUNCTIONS.has(state.function)) {
            text = `${text} ${unitLabel(state, ctx.skin)}`.trim();
          }
          f.textContent = text;
        }
      }

      // Status annunciators (Hold/Rel/Auto/A-Hold/Crest/Rec/Max/Min/Avg) and
      // the low-battery indicator — routed from state via skin.json "icons"
      // and "battery_low" (overlay.js ctx.lightIcons / ctx.lightBattery).
      ctx.lightIcons(state.icons);
      ctx.lightBattery(state.battery_low);
    },
  };
})();
