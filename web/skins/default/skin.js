/* Default skin render module.
 *
 * Self-made stylized BM78xBT display (distributed with the repo). The reading
 * is rendered as monospace text (value_text) instead of 7-segment bars; the
 * function name and RTC are written as text elements.
 *
 * Register: window.__bm_skins.default = { render(state, ctx) { ... } }.
 */
window.__bm_skins = window.__bm_skins || {};
window.__bm_skins.default = (function () {
  // Right edge of the digit area for the monospace reading text (from meter.svg).
  const RIGHT_X = 317;

  // Build the display string from the semantic cells: blanks for empty cells
  // and '.' after the cell that carries the decimal point. Sign is applied by
  // the caller so leading-zero stripping can work on the value alone.
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

  // "Light all" self-test (state.mode == "all"): the reading shows "88888"
  // and every unit, prefix, icon and annunciator turns on at once.
  function lightAllDefault(ctx) {
    const skin = ctx.skin;
    const vt = ctx.byId('value_text');
    if (vt) {
      vt.textContent = '88888';
      vt.setAttribute('text-anchor', 'end');
      vt.setAttribute('x', RIGHT_X);
    }
    ctx.lightAllUnits();
    ctx.lightAllPrefixes();
    ctx.lightAllIcons();
    if (skin.battery_low) ctx.show(skin.battery_low, true);
    if (skin.sign) ctx.show(skin.sign, true);
    const fn = skin.function;
    if (fn && fn.type === 'text' && fn.id) {
      const f = ctx.byId(fn.id);
      if (f) f.textContent = 'ALL';
    }
    if (skin.rtc_label) {
      const r = ctx.byId(skin.rtc_label);
      if (r) r.textContent = '2026-08-06 12:34:56.789';
    }
  }

  return {
    name: 'default',
    render(state, ctx) {
      // Self-test: light every element the skin owns.
      if (state.mode === 'all') {
        lightAllDefault(ctx);
        return;
      }

      const el = ctx.byId('value_text');
      if (el) {
        let text = valueText(state);
        // The default skin does not zero-pad numeric readings (the official
        // meter does); drop leading zeros like "00.250" -> "0.250".
        if (state.mode === 'numeric') text = stripLeadingZeros(text);
        if (state.sign) text = '-' + text;
        el.textContent = text;
        // The default skin right-aligns the reading (the official meter
        // left-aligns some ASCII states; that is an official-skin decision).
        el.setAttribute('text-anchor', 'end');
        el.setAttribute('x', RIGHT_X);
      }

      ctx.lightUnits(state.unit);
      ctx.lightPrefixes(state.unit, state.prefix);
      ctx.lightIcons(state.icons);
      ctx.lightBattery(state.battery_low);

      // Function name as text (skin.json: { type: "text", id: "fn_text" }).
      // skin.json "function_labels" overrides the SDK's canonical function
      // names for display; anything not listed falls back to the canonical
      // name (so the SDK's protocol-faithful names stay untouched).
      const fn = ctx.skin.function;
      if (fn && fn.type === 'text' && fn.id) {
        const f = ctx.byId(fn.id);
        if (f) {
          const labels = ctx.skin.function_labels || {};
          f.textContent = labels[state.function] || state.function || '';
        }
      }

      // RTC timestamp as text (skin.json: "rtc_label": "rtc_text").
      if (ctx.skin.rtc_label) {
        const r = ctx.byId(ctx.skin.rtc_label);
        if (r) r.textContent = state.rtc || '';
      }
    },
  };
})();
