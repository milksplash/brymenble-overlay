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

  let skin;
  try {
    skin = await (await fetch(`${base}/skin.json`)).json();
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
  try {
    await loadScript(`${base}/${skin.script || 'skin.js'}`);
  } catch (e) {
    console.error(e);
    document.body.textContent = `Failed to load skin script for "${skinName}".`;
    return;
  }
  const impl = window.__bm_skins && window.__bm_skins[skinName];
  if (!impl || typeof impl.render !== 'function') {
    console.error(`Skin "${skinName}" did not register a render() on window.__bm_skins.`);
    document.body.textContent = `Skin "${skinName}" has no render module.`;
    return;
  }

  svg.style.visibility = 'visible';

  // Paint everything off immediately, then poll for live state.
  impl.render(
    { value_digits: [], sign: false, unit: null, prefix: null, icons: {}, battery_low: false },
    ctx
  );

  async function poll() {
    try {
      const res = await fetch('/state.json', { cache: 'no-store' });
      if (res.ok) impl.render(await res.json(), ctx);
    } catch (e) { /* server not up yet — keep polling */ }
  }
  poll();
  setInterval(poll, 200);
})();
