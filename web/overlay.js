/* BM78xBT display overlay — connects to /state.json, drives the active skin.
 *
 * Skin selection: ?skin=NAME (defaults to "default").
 * A skin is a folder under /skins/NAME containing skin.json, meter.svg and
 * skin.css. skin.json maps semantic render-state keys to SVG element ids.
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

  function show(id, on) {
    const el = byId(id);
    if (el) el.style.display = on ? 'inline' : 'none';
  }

  const SEGS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'dp'];

  function apply(state) {
    svg.style.visibility = 'visible';

    // digits (right-aligned in the cell)
    const cells = state.value_digits || [];
    const offset = skin.digits - cells.length;
    for (let i = 0; i < skin.digits; i++) {
      const cell = i >= offset ? cells[i - offset] : null;
      for (const seg of SEGS) {
        const lit = cell && (seg === 'dp' ? cell.dp : cell.segments.includes(seg));
        show(`${skin.digit_prefix}${i}_${seg}`, lit);
      }
    }

    if (skin.sign) show(skin.sign, !!state.sign);

    if (skin.unit) {
      for (const [u, id] of Object.entries(skin.unit)) {
        if (id) show(id, state.unit === u);
      }
    }
    if (skin.prefix) {
      for (const [p, id] of Object.entries(skin.prefix)) {
        if (id) show(id, state.prefix === p);
      }
    }
    if (skin.icons) {
      for (const [key, id] of Object.entries(skin.icons)) {
        if (id) show(id, !!(state.icons && state.icons[key]));
      }
    }
    if (skin.battery_low) show(skin.battery_low, !!state.battery_low);

    if (skin.function_label) {
      const el = byId(skin.function_label);
      if (el) el.textContent = state.function || '';
    }
    if (skin.rtc_label) {
      const el = byId(skin.rtc_label);
      if (el) el.textContent = state.rtc || '';
    }
  }

  // Paint everything off immediately, then poll for live state.
  apply({ value_digits: [], sign: false, unit: null, prefix: null, icons: {}, battery_low: false });

  async function poll() {
    try {
      const res = await fetch('/state.json', { cache: 'no-store' });
      if (res.ok) apply(await res.json());
    } catch (e) { /* server not up yet — keep polling */ }
  }
  poll();
  setInterval(poll, 200);
})();
