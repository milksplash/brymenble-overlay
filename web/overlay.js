/* BM78xBT display overlay — thin host.
 *
 * Loads a skin (folder under /skins/NAME: skin.json, meter.svg, skin.css)
 * plus the skin's render module (skin.json "script", default "skin.js"), then
 * polls /state.json and hands each semantic state to the skin's render().
 *
 * Skins receive a shared context (`ctx`) with small paint helpers:
 *   byId(id), show(id, on), lightDigits(cells, offset), lightSign(on),
 *   lightUnits(unit), lightPrefixes(unit, prefix), lightIcons(icons),
 *   lightBattery(low), plus the parsed `skin` config.
 *
 * A skin module registers itself on window.__bm_skins[NAME]:
 *   window.__bm_skins = window.__bm_skins || {};
 *   window.__bm_skins.default = { render(state, ctx) { ... } };
 */
(async function () {
  const params = new URLSearchParams(location.search);
  const skinName = params.get('skin') || 'default';
  const base = `skins/${skinName}`;

  // Bump this when the skin-loading / renderer code changes so a stale
  // skin.js isn't served from cache across an OBS Browser Source reload.
  const VERSION = '1';

  // ?debug=1 shows skin render errors on the page (the poll loop would
  // otherwise swallow them) — essential while authoring a skin.
  const debug = /^(1|true)$/i.test(params.get('debug') || '');

  let skin;
  try {
    skin = await (await fetch(`${base}/skin.json`, { cache: 'no-store' })).json();
  } catch (e) {
    console.error(`Failed to load skin "${skinName}":`, e);
    document.body.textContent = `Failed to load skin "${skinName}".`;
    return;
  }

  // Skin stylesheet
  try {
    const css = await (await fetch(`${base}/skin.css`)).text();
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  } catch (e) { /* optional */ }

  // Skin meter.svg -> injected into #meter
  const svg = document.getElementById('meter');
  const svgText = await (await fetch(`${base}/meter.svg`)).text();
  const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
  const root = doc.documentElement;
  for (const attr of Array.from(root.attributes)) {
    if (attr.name === 'id') continue;  // keep our container id (#meter); skins carry their own (e.g. svg1)
    svg.setAttribute(attr.name, attr.value);
  }
  while (root.firstChild) svg.appendChild(root.firstChild);

  const byId = (id) => svg.querySelector(`#${CSS.escape(id)}`);
  const show = (id, on) => {
    const el = byId(id);
    if (el) el.style.display = on ? 'inline' : 'none';
  };

  const SEGS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'dp'];

  // Shared paint helpers, bound to this skin's config.
  const ctx = {
    skin,
    byId,
    show,
    lightDigits(cells, offset) {
      cells = cells || [];
      for (let i = 0; i < skin.digits; i++) {
        const j = i - offset;
        const cell = (j >= 0 && j < cells.length) ? cells[j] : null;
        for (const seg of SEGS) {
          const lit = cell && (seg === 'dp' ? cell.dp : cell.segments.includes(seg));
          show(`${skin.digit_prefix}${i}_${seg}`, lit);
        }
      }
    },
    lightSign(on) { if (skin.sign) show(skin.sign, !!on); },
    lightUnits(unit) {
      if (!skin.unit) return;
      for (const [u, id] of Object.entries(skin.unit)) if (id) show(id, unit === u);
    },
    lightPrefixes(unit, prefix) {
      if (!skin.prefix) return;
      const ids = new Set();
      for (const m of Object.values(skin.prefix)) {
        for (const id of Object.values(m)) if (id) ids.add(id);
      }
      const target = unit && skin.prefix[unit] ? skin.prefix[unit][prefix] : null;
      for (const id of ids) show(id, id === target);
    },
    lightIcons(icons) {
      if (!skin.icons) return;
      for (const [key, id] of Object.entries(skin.icons)) {
        if (id) show(id, !!(icons && icons[key]));
      }
    },
    lightBattery(low) { if (skin.battery_low) show(skin.battery_low, !!low); },
    // "Light all" helpers for the skin self-test mode (state.mode == "all").
    lightAllUnits() {
      if (!skin.unit) return;
      for (const id of Object.values(skin.unit)) if (id) show(id, true);
    },
    lightAllPrefixes() {
      if (!skin.prefix) return;
      for (const m of Object.values(skin.prefix)) {
        for (const id of Object.values(m)) if (id) show(id, true);
      }
    },
    lightAllIcons() {
      if (!skin.icons) return;
      for (const id of Object.values(skin.icons)) if (id) show(id, true);
    },
  };

  // On-page error surface for ?debug=1: render exceptions that the poll loop
  // would otherwise swallow are shown in a bottom strip (plus console.error).
  let debugStrip = null;
  function reportError(msg, e) {
    console.error(msg, e);
    if (!debug) return;
    if (!debugStrip) {
      debugStrip = document.createElement('div');
      debugStrip.style.cssText =
        'position:fixed;left:0;right:0;bottom:0;z-index:9999;' +
        'background:#7a1515;color:#fff;font:12px/1.5 monospace;' +
        'padding:6px 10px;white-space:pre-wrap;word-break:break-all;';
      document.body.appendChild(debugStrip);
    }
    const detail = e && e.stack
      ? e.stack.split('\n').slice(0, 4).join('\n')
      : (e ? String(e) : '');
    debugStrip.textContent = `${msg}\n${detail}`;
    debugStrip.style.outline = '2px solid #ff6b6b';
    clearTimeout(reportError._t);
    reportError._t = setTimeout(() => {
      if (debugStrip) debugStrip.style.outline = 'none';
    }, 400);
  }

  // Built-in generic LCD renderer. Used when a skin declares
  // "renderer": "lcd" or ships no working render module — so a skin can be
  // just skin.json + meter.svg. It drives 7-seg digits, sign, units, prefixes,
  // icons, battery and function icons purely from skin.json. Per-function
  // right alignment is declared with skin.json "right_aligned" (e.g.
  // ["Duty Cycle (%)"]).
  function lcdRenderer() {
    let iconFunctions = null;
    function buildIconMap(map) {
      const m = new Map();
      for (const [name, idOrIds] of Object.entries(map)) {
        const ids = Array.isArray(idOrIds) ? idOrIds : [idOrIds];
        for (const id of ids) {
          if (!id) continue;
          if (!m.has(id)) m.set(id, new Set());
          m.get(id).add(name);
        }
      }
      return m;
    }
    function lightAll(ctx) {
      const skin = ctx.skin;
      if (Array.isArray(skin.hidden)) {
        for (const id of skin.hidden) if (id) ctx.show(id, false);
      }
      const noDp = new Set(skin.no_dp || []);
      for (let d = 0; d < skin.digits; d++) {
        for (const s of SEGS) {
          if (s === 'dp' && noDp.has(d)) continue;  // no decimal point here
          ctx.show(`${skin.digit_prefix}${d}_${s}`, true);
        }
      }
      ctx.lightAllUnits();
      ctx.lightAllPrefixes();
      ctx.lightAllIcons();
      if (skin.battery_low) ctx.show(skin.battery_low, true);
      if (skin.sign) ctx.show(skin.sign, true);
      const fn = skin.function;
      if (fn && fn.type === 'icons' && fn.map) {
        for (const idOrIds of Object.values(fn.map)) {
          const ids = Array.isArray(idOrIds) ? idOrIds : [idOrIds];
          for (const id of ids) if (id) ctx.show(id, true);
        }
      }
    }
    return function render(state, ctx) {
      const skin = ctx.skin;
      if (state.mode === 'all') { lightAll(ctx); return; }
      if (Array.isArray(skin.hidden)) {
        for (const id of skin.hidden) if (id) ctx.show(id, false);
      }
      const rightAligned = new Set(skin.right_aligned || []);
      const cells = state.value_digits || [];
      const offset = rightAligned.has(state.function)
        ? Math.max(0, skin.digits - cells.length)
        : 0;
      ctx.lightDigits(cells, offset);
      ctx.lightSign(state.sign);
      ctx.lightUnits(state.unit);
      ctx.lightPrefixes(state.unit, state.prefix);
      ctx.lightIcons(state.icons);
      ctx.lightBattery(state.battery_low);
      const fn = skin.function;
      if (fn && fn.type === 'icons' && fn.map) {
        if (!iconFunctions) iconFunctions = buildIconMap(fn.map);
        for (const [id, names] of iconFunctions) {
          ctx.show(id, names.has(state.function));
        }
      }
    };
  }

  // Load the skin's render module (skin.json "script", default "skin.js").
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error(`Failed to load skin script: ${src}`));
      document.head.appendChild(s);
    });
  }
  // Resolve the render implementation:
  //   1. "renderer": "lcd" -> built-in generic LCD renderer, no file needed.
  //   2. skin.json "script" (default "skin.js") -> the module registers
  //      window.__bm_skins[skinName].
  //   3. No usable module -> fall back to the built-in LCD renderer, so a skin
  //      can be just skin.json + meter.svg (skin.js is optional).
  let impl = null;
  const scriptName = skin.script || 'skin.js';
  if (skin.renderer !== 'lcd') {
    try {
      // Always append a cache-buster so a stale skin.js can't survive an OBS
      // Browser Source reload during skin iteration; ?debug=1 uses a stronger
      // per-load timestamp to bypass the cache entirely.
      const buster = debug ? '?v=' + Date.now() : '?v=' + VERSION;
      await loadScript(`${base}/${scriptName}${buster}`);
      impl = window.__bm_skins && window.__bm_skins[skinName];
    } catch (e) {
      console.warn(`[${skinName}] no script at ${base}/${scriptName} — using built-in LCD renderer.`);
    }
  }
  if (!impl || typeof impl.render !== 'function') {
    if (skin.script) {
      console.warn(`[${skinName}] "${skin.script}" loaded but registered no render() — using built-in LCD renderer.`);
    }
    impl = { name: skinName, render: lcdRenderer() };
  }

  svg.style.visibility = 'visible';

  // Paint everything off immediately, then poll for live state.
  try {
    impl.render(
      { value_digits: [], sign: false, unit: null, prefix: null, icons: {}, battery_low: false },
      ctx
    );
  } catch (e) {
    reportError(`[${skinName}] initial render() threw`, e);
  }

  async function poll() {
    let state;
    try {
      const res = await fetch('/state.json', { cache: 'no-store' });
      if (!res.ok) return;
      state = await res.json();
    } catch (e) {
      /* server not up yet — keep polling */
      return;
    }
    // Render exceptions are surfaced (console + ?debug=1 strip) instead of
    // being silently swallowed, so a skin bug can't hide as a blank reading.
    try {
      impl.render(state, ctx);
    } catch (e) {
      reportError(`[${skinName}] skin.render() threw`, e);
    }
  }
  poll();
  setInterval(poll, 200);
})();
