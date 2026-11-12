/*
 * Mini-runtime do painel público.
 *
 * Os gráficos da página foram escritos contra uma API pequena (`dash.data`, `dash.draw`, `dash.calc`,
 * `dash.colors`). Este arquivo implementa essa API para uma página estática: lê `data/<conjunto>.json`
 * (gerados por `malpipe site`), calcula os derivados e redesenha tudo quando os dados chegam ou a
 * largura muda. Sem dependências além do d3, carregado antes.
 */
(function () {
  'use strict';

  const store = {};   // id -> {status, data}
  const calcs = {};   // id -> {inputs, fn}
  const draws = {};   // nome -> fn(el)
  const listeners = [];
  const colors = Array.from({ length: 8 }, (_, i) => `var(--series-${i + 1})`);

  function data(id) {
    if (calcs[id]) {
      const c = calcs[id];
      const inputs = c.inputs.map(data);
      const bad = inputs.find((d) => d.status !== 'ok');
      if (bad) return { status: bad.status, data: [] };
      try {
        return { status: 'ok', data: c.fn(...inputs.map((d) => d.data)) };
      } catch (err) {
        console.error(`calc ${id}`, err);
        return { status: 'error', data: [] };
      }
    }
    return store[id] || { status: 'loading', data: [] };
  }

  // Atributos de apresentação SVG não aceitam var(): passa esses valores para `style`.
  function resolveVars(root) {
    root.querySelectorAll('[fill^="var("], [stroke^="var("]').forEach((node) => {
      for (const attr of ['fill', 'stroke']) {
        const v = node.getAttribute(attr);
        if (v && v.startsWith('var(')) { node.style[attr] = v; node.removeAttribute(attr); }
      }
    });
  }

  function redraw() {
    for (const fn of listeners) { try { fn(); } catch (err) { console.error(err); } }
    for (const [name, fn] of Object.entries(draws)) {
      document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => {
        try { fn(el); resolveVars(el); } catch (err) { console.error(`draw ${name}`, err); }
      });
    }
  }

  function datasetIds() {
    const ids = new Set();
    document.querySelectorAll('[data-source]').forEach((el) =>
      el.getAttribute('data-source').split(/\s+/).filter(Boolean).forEach((id) => ids.add(id)));
    Object.values(calcs).forEach((c) => c.inputs.forEach((id) => ids.add(id)));
    Object.keys(calcs).forEach((id) => ids.delete(id));
    return [...ids];
  }

  async function load(id) {
    try {
      const res = await fetch(`data/${id}.json`, { cache: 'no-cache' });
      if (!res.ok) throw new Error(`${res.status}`);
      const rows = await res.json();
      store[id] = { status: 'ok', data: Array.isArray(rows) ? rows : [] };
    } catch (err) {
      console.error(`dataset ${id}`, err);
      store[id] = { status: 'error', data: [] };
    }
    redraw();
  }

  window.dash = {
    data,
    colors,
    calc(id, spec) { calcs[id] = spec; },
    draw(name, fn) { draws[name] = fn; },
    onData(fn) { listeners.push(fn); },
    refresh() { redraw(); },
  };

  document.addEventListener('DOMContentLoaded', () => {
    redraw();
    datasetIds().forEach(load);
    fetch('data/meta.json', { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : null))
      .then((meta) => {
        const el = document.querySelector('[data-meta="generated_at"]');
        if (meta && el) el.textContent = new Date(meta.generated_at).toLocaleDateString('pt-BR', { dateStyle: 'long' });
      })
      .catch(() => {});
    let width = window.innerWidth;
    let timer;
    window.addEventListener('resize', () => {
      if (window.innerWidth === width) return;
      width = window.innerWidth;
      clearTimeout(timer);
      timer = setTimeout(redraw, 150);
    });
  });
})();
