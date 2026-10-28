// DeepECG-Bench: one table, drawn in the browser from three data files.
//
//   data/catalogue.json   hand-edited prose: families, tasks, metrics, architectures
//   data/registry.json    machine facts exported from deepecgkit (tools/export_registry.py)
//   data/results.json     aggregated runs (tools/build_results.py)
//
// The top half of this file is pure and is what tools/tests/app.test.mjs exercises; the
// bottom half is the DOM. No dependencies, no build step.

const DATA_FILES = ["catalogue", "registry", "results"];
const DEFAULT_METRIC = "f1";
const DIGITS = 3;
const PLOT_LABELS = {
  "confusion-matrix": "Confusion matrix",
  "calibration-curve": "Calibration curve",
  "loss-curve": "Loss curve",
};
const EXPLAIN_LABELS = {
  gradient_attribution: "gradient attribution",
  occlusion: "occlusion",
  class_activation: "class activation maps",
};
const DOCS = "https://stevenah.github.io/deepecg-kit/benchmark/";

// ── Pure logic ──────────────────────────────────────────────────────────────────────────

/** Join the three files into the rows, columns and counts the page shows. */
export function buildModel(catalogue, registry, results) {
  const families = catalogue.families ?? [];
  const familyIndex = new Map(families.map((f, i) => [f.id, i]));
  const tasks = catalogue.tasks ?? [];
  const taskIds = new Set(tasks.map((t) => t.id));
  const prose = new Map((catalogue.models ?? []).map((m) => [m.name, m]));
  const canonical = registry.meta?.canonical_probe ?? "12x5";

  const resultsOf = new Map();
  for (const r of results?.rows ?? []) {
    if (!taskIds.has(r.task) || !registry.models[r.model]) continue;
    if (!resultsOf.has(r.model)) resultsOf.set(r.model, {});
    resultsOf.get(r.model)[r.task] = r;
  }

  const rows = Object.values(registry.models).map((m) => {
    const p = prose.get(m.registry_name) ?? {};
    const family = families[familyIndex.get(p.family)] ?? null;
    const probes = m.probes ?? {};
    const title = m.display_name || m.registry_name;
    const row = {
      name: m.registry_name,
      title,
      family: family?.id ?? null,
      familyLabel: family?.label ?? null,
      familyIndex: family ? familyIndex.get(family.id) : families.length,
      year: p.paper?.year ?? null,
      params: probes[canonical]?.params_trainable ?? null,
      shapes: shapesOf(probes, registry.meta?.probes ?? {}, tasks, canonical),
      featureDim: probes[canonical]?.feature_dim ?? null,
      className: m.class ?? null,
      minInput: m.min_input_length ?? null,
      maxInput: m.max_input_length ?? null,
      summary: p.summary ?? m.description ?? null,
      description: p.description ?? p.summary ?? m.description ?? null,
      paper: p.paper ?? null,
      codeUrl: p.code_url ?? null,
      adaptedFrom: p.adapted_from ?? null,
      notes: p.notes ?? null,
      deviations: p.deviations ?? [],
      explain: p.explain ?? null,
      results: resultsOf.get(m.registry_name) ?? {},
    };
    row.text = [
      row.name, title, row.familyLabel, row.summary, p.description, row.className,
      p.paper?.title, p.paper?.authors, p.paper?.venue,
    ].filter(Boolean).join(" ").toLowerCase();
    return row;
  });

  // Default order: family, then parameter count, as Table 1 of the article.
  rows.sort((a, b) =>
    a.familyIndex - b.familyIndex
    || (a.params ?? Infinity) - (b.params ?? Infinity)
    || a.name.localeCompare(b.name));
  rows.forEach((row, i) => { row.order = i; });

  const metrics = metricsOf(catalogue, registry, results);
  const measured = rows.reduce((n, row) => n + Object.keys(row.results).length, 0);
  return {
    families,
    tasks,
    metrics,
    rows,
    canonicalShape: registry.meta?.probes?.[canonical] ?? null,
    defaultMetric: (metrics.find((m) => m.id === DEFAULT_METRIC) ?? metrics[0])?.id ?? null,
    counts: { models: rows.length, tasks: tasks.length, measured, total: rows.length * tasks.length },
    provenance: {
      generated: results?.generated ?? null,
      resultsKit: results?.kit_version ?? null,
      nRuns: results?.n_runs ?? null,
      confidence: results?.confidence_level ?? null,
      registryKit: registry.meta?.kit_version ?? null,
      registrySha: registry.meta?.kit_git_sha ?? null,
    },
  };
}

/** Parameter counts per input shape, canonical shape first, with the tasks that use each. */
function shapesOf(probes, shapeDefs, tasks, canonical) {
  return Object.keys(probes)
    .filter((key) => probes[key]?.status === "ok" && shapeDefs[key])
    .sort((a, b) => (b === canonical) - (a === canonical)
      || shapeDefs[b].input_channels - shapeDefs[a].input_channels
      || shapeDefs[b].output_size - shapeDefs[a].output_size)
    .map((key) => ({
      key,
      channels: shapeDefs[key].input_channels,
      outputs: shapeDefs[key].output_size,
      params: probes[key].params_trainable,
      tasks: tasks
        .filter((t) => `${t.input_channels}x${t.output_size}` === key)
        .map((t) => t.short),
    }));
}

/** The metrics that occur in the results, in catalogue order; unknown ones go last. */
function metricsOf(catalogue, registry, results) {
  const present = new Set();
  for (const r of results?.rows ?? []) for (const id of Object.keys(r.metrics ?? {})) present.add(id);
  const known = (catalogue.metrics ?? []).filter((m) => present.has(m.id));
  const lower = new Set(registry.constants?.lower_is_better ?? []);
  const unknown = [...present]
    .filter((id) => !known.some((m) => m.id === id))
    .sort()
    .map((id) => ({ id, label: id, name: id, better: lower.has(id) ? "lower" : "higher", group: null }));
  return [...known, ...unknown];
}

/** A paper as the table cites it: "Hannun et al. 2019", "Hochreiter and Schmidhuber 1997". */
export function citation(paper) {
  if (!paper) return null;
  const names = (paper.authors ?? "").split(",").map((name) => name.trim()).filter(Boolean);
  const who = names.length > 2 ? `${names[0]} et al.` : names.join(" and ");
  return [who, paper.year].filter(Boolean).join(" ") || paper.title || null;
}

/** A run that predicted no positive case: precision and recall are both exactly zero. */
export function isDegenerate(result) {
  return result?.metrics?.precision?.mean === 0 && result?.metrics?.recall?.mean === 0;
}

/**
 * What one table cell holds. "none": the pair was never run. "na": it was run, but this
 * metric is not defined for the task (accuracy on a multi-label task, for instance).
 */
export function cellFor(row, taskId, metricId) {
  const result = row.results[taskId];
  if (!result) return { state: "none" };
  const m = metricId ? result.metrics?.[metricId] : null;
  if (!m || m.mean == null) return { state: "na" };
  return { state: "value", ...m, degenerate: isDegenerate(result) };
}

/** The best value per task for one metric; absent where fewer than two pairs have one. */
export function bestByTask(rows, tasks, metric) {
  const best = new Map();
  if (!metric?.better) return best;
  for (const task of tasks) {
    const values = rows
      .map((row) => cellFor(row, task.id, metric.id))
      .filter((c) => c.state === "value")
      .map((c) => c.mean);
    if (values.length >= 2) {
      best.set(task.id, metric.better === "lower" ? Math.min(...values) : Math.max(...values));
    }
  }
  return best;
}

/** Sort a copy of the rows. Empty cells go last in both directions; ties keep default order. */
export function sortRows(rows, sort, metricId) {
  if (!sort) return [...rows].sort((a, b) => a.order - b.order);
  const sign = sort.dir === "desc" ? -1 : 1;
  const key = (row) => {
    if (sort.key === "name") return row.title.toLowerCase();
    if (sort.key === "params") return row.params;
    const cell = cellFor(row, sort.key, metricId);
    return cell.state === "value" ? cell.mean : null;
  };
  return [...rows].sort((a, b) => {
    const x = key(a);
    const y = key(b);
    if (x == null || y == null) return (x == null) - (y == null) || a.order - b.order;
    if (x < y) return -sign;
    if (x > y) return sign;
    return a.order - b.order;
  });
}

/** Header click cycle: best or A–Z first, then reversed, then back to the default order. */
export function nextSort(sort, key, metric) {
  const text = key === "name" || key === "params";
  const first = text || metric?.better === "lower" ? "asc" : "desc";
  if (!sort || sort.key !== key) return { key, dir: first };
  if (sort.dir === first) return { key, dir: first === "asc" ? "desc" : "asc" };
  return null;
}

/**
 * The sort to keep when the metric changes. A task column sorted best-first stays
 * best-first, which means flipping the direction between a higher-is-better and a
 * lower-is-better metric.
 */
export function sortForMetric(sort, before, after) {
  if (!sort || sort.key === "name" || sort.key === "params") return sort;
  if ((before?.better === "lower") === (after?.better === "lower")) return sort;
  return { key: sort.key, dir: sort.dir === "asc" ? "desc" : "asc" };
}

/** Family filter and search; every search word must occur somewhere in the row's text. */
export function matches(row, state) {
  if (state.family && row.family !== state.family) return false;
  const words = (state.q ?? "").toLowerCase().split(/\s+/).filter(Boolean);
  return words.every((w) => row.text.includes(w));
}

export function formatValue(value) {
  return value == null ? "" : value.toFixed(DIGITS);
}

/** Parameter count in millions with three decimals, as in the article. */
export function formatParams(count) {
  return count == null ? "" : (count / 1e6).toFixed(3);
}

/** Bar length on a fixed 0–1 scale; none for a metric without a direction (temperature). */
export function barFraction(value, metric) {
  if (!metric?.better || value == null) return null;
  return Math.min(1, Math.max(0, value));
}

/** Page state from the query string; anything unrecognised falls back to its default. */
export function parseState(search, model) {
  const params = new URLSearchParams(search);
  const sortKeys = new Set(["name", "params", ...model.tasks.map((t) => t.id)]);
  const metric = params.get("metric");
  const key = params.get("sort");
  const family = params.get("family");
  const open = params.get("model");
  return {
    metric: model.metrics.some((m) => m.id === metric) ? metric : model.defaultMetric,
    sort: sortKeys.has(key) ? { key, dir: params.get("dir") === "asc" ? "asc" : "desc" } : null,
    family: model.families.some((f) => f.id === family) ? family : "",
    q: params.get("q") ?? "",
    open: model.rows.some((r) => r.name === open) ? open : null,
  };
}

/** The query string for a state, with defaults left out so a plain URL stays plain. */
export function toSearch(state, model) {
  const params = new URLSearchParams();
  if (state.metric && state.metric !== model.defaultMetric) params.set("metric", state.metric);
  if (state.sort) {
    params.set("sort", state.sort.key);
    params.set("dir", state.sort.dir);
  }
  if (state.family) params.set("family", state.family);
  if (state.q) params.set("q", state.q);
  if (state.open) params.set("model", state.open);
  const text = params.toString();
  return text ? `?${text}` : "";
}

// ── DOM ─────────────────────────────────────────────────────────────────────────────────

/** Create an element. Children are nodes or strings; strings become text, never markup. */
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (name === "class") el.className = value;
    else if (name.startsWith("on")) el.addEventListener(name.slice(2), value);
    else el.setAttribute(name, value === true ? "" : value);
  }
  return fill(el, children);
}

/** Replace an element's children. Like h(), takes nested arrays and skips null and false. */
function fill(el, ...children) {
  el.replaceChildren(...children.flat(Infinity).filter((c) => c != null && c !== false));
  return el;
}

const hidden = (text) => h("span", { class: "visually-hidden" }, text);
const external = (href, text) => h("a", { href, rel: "noopener" }, text);
const plural = (n, word) => `${n.toLocaleString("en-US")} ${word}${n === 1 ? "" : "s"}`;
const capitalise = (text) => text.charAt(0).toUpperCase() + text.slice(1);

async function fetchJson(name) {
  const response = await fetch(new URL(`./data/${name}.json`, import.meta.url), { cache: "no-cache" });
  if (!response.ok) throw new Error(`${name}.json could not be loaded (HTTP ${response.status})`);
  return response.json();
}

function mount(model, resultsError) {
  const $ = (id) => document.getElementById(id);
  const state = parseState(location.search, model);
  const metricOf = (id) => model.metrics.find((m) => m.id === id) ?? null;
  const rowEls = new Map();

  // Controls: two groups of toggle buttons, one pressed at a time, as on ECGBench.
  const familyPills = pills($("family"),
    [{ id: "", label: "All" }, ...model.families.filter((f) => model.rows.some((r) => r.family === f.id))],
    (id) => { state.family = id; familyPills.set(id); refresh(); });
  // Classification metrics only; calibration stays in each architecture's panel.
  const shown = model.metrics.filter((m) => !m.group);
  if (!shown.some((m) => m.id === state.metric)) state.metric = model.defaultMetric;
  const metricPills = pills($("metric"), shown.map((m) => ({ id: m.id, label: m.label, title: m.name, group: "Metric" })),
    (id) => {
      const before = metricOf(state.metric);
      state.metric = id;
      metricPills.set(id);
      state.sort = sortForMetric(state.sort, before, metricOf(state.metric));
      fillCells();
      notes();
      reorder();
    });
  $("q").value = state.q;
  familyPills.set(state.family);
  metricPills.set(state.metric);

  // Version line under the hero links: static once the data is in.
  const version = versionLine(model.provenance);
  if (version.length) fill($("version"), version).hidden = false;

  // Table.
  const shape = model.canonicalShape;
  const headers = [
    { key: "name", label: "Architecture" },
    {
      key: "params", label: "Parameters (M)", num: true,
      title: `Trainable parameters in millions${shape
        ? `, for ${plural(shape.input_channels, "lead")} and ${plural(shape.output_size, "output")}` : ""}`,
    },
    ...model.tasks.map((t) => ({ key: t.id, label: t.short, num: true, title: t.title, note: t.note })),
    { key: "ref", label: "Reference", fixed: true, title: "The publication the implementation follows, and its code" },
  ];
  const headEls = new Map();
  const caption = h("caption", { class: "visually-hidden" });
  const thead = h("thead", {}, h("tr", {}, headers.map((col) => {
    const th = h("th", { scope: "col", class: col.num ? "num" : null, title: col.title },
      col.fixed ? col.label : h("button", { class: "sort-btn", type: "button", onclick: () => setSort(col.key) }, col.label,
        col.note ? [h("span", { class: "mark", "aria-hidden": "true" }, "*"), hidden(" (see note below)")] : null));
    if (!col.fixed) headEls.set(col.key, th);
    return th;
  })));
  const empty = h("tr", { class: "empty", hidden: true },
    h("td", { colspan: headers.length }, "No architecture matches the search and family filter."));
  const tbody = h("tbody");
  for (const row of model.rows) {
    const toggle = h("button", {
      class: "row-toggle", type: "button", "aria-expanded": "false", onclick: () => setOpen(row.name),
    }, h("span", { class: "chev", "aria-hidden": "true" }), h("span", { class: "row-name" }, row.title));
    const cells = new Map(model.tasks.map((t) => [t.id, h("td", { class: "num" })]));
    const tr = h("tr", { class: "row", id: `row-${row.name}` },
      h("th", { scope: "row" }, toggle, row.familyLabel ? h("span", { class: "row-sub" }, row.familyLabel) : null),
      h("td", { class: "num" }, row.params == null ? "" : formatParams(row.params)),
      [...cells.values()],
      h("td", { class: "ref" }, referenceOf(row)));
    rowEls.set(row.name, { tr, toggle, cells, panel: null });
  }
  const table = h("table", { id: "bench" }, caption, thead, tbody);
  $("table-wrap").replaceChildren(table);

  // Footer: static once the data is in.
  $("provenance").replaceChildren(...provenanceLine(model.provenance));

  function fillCells() {
    const metric = metricOf(state.metric);
    const best = bestByTask(model.rows, model.tasks, metric);
    for (const row of model.rows) {
      for (const task of model.tasks) {
        const td = rowEls.get(row.name).cells.get(task.id);
        const cell = cellFor(row, task.id, state.metric);
        if (cell.state === "none") {
          fill(td, h("span", { class: "muted", "aria-hidden": "true" }, "—"), hidden("not run"));
        } else if (cell.state === "na") {
          fill(td, h("span", { class: "muted" }, "n/a"), hidden(" (not defined for this task)"));
        } else {
          const fraction = barFraction(cell.mean, metric);
          fill(td,
            h("span", { class: cell.mean === best.get(task.id) ? "val best" : "val" }, formatValue(cell.mean)),
            cell.degenerate ? [h("span", { class: "mark", "aria-hidden": "true" }, "†"), hidden(" (no positive predictions)")] : null,
            cell.n >= 2 && cell.std != null ? h("span", { class: "sd" }, `± ${formatValue(cell.std)}`) : null,
            fraction == null ? null : h("span", { class: "bar", "aria-hidden": "true" },
              h("i", { style: `width:${(fraction * 100).toFixed(1)}%` })),
          );
        }
      }
    }
    caption.textContent = metric
      ? `Architectures in DeepECG-Kit with their ${metric.name} on each task`
      : "Architectures in DeepECG-Kit";
  }

  // Rows are built once and then moved, never rebuilt, so an open panel keeps its loaded
  // plots. Moving happens only on a sort or metric change, which come from controls
  // outside the table body; opening a row or typing in the search box moves nothing.
  function reorder() {
    const active = document.activeElement;
    const nodes = [];
    for (const row of sortRows(model.rows, state.sort, state.metric)) {
      const els = rowEls.get(row.name);
      nodes.push(els.tr);
      if (els.panel) nodes.push(els.panel);
    }
    tbody.append(...nodes, empty);
    if (active !== document.activeElement && tbody.contains(active)) active.focus({ preventScroll: true });
    refresh();
  }

  function refresh() {
    let visible = 0;
    for (const row of model.rows) {
      const els = rowEls.get(row.name);
      const show = matches(row, state);
      els.tr.hidden = !show;
      if (els.panel) els.panel.hidden = !show || state.open !== row.name;
      if (show) visible += 1;
    }
    empty.hidden = visible > 0;

    for (const [key, th] of headEls) {
      if (state.sort?.key === key) th.setAttribute("aria-sort", state.sort.dir === "asc" ? "ascending" : "descending");
      else th.removeAttribute("aria-sort");
    }
    history.replaceState(null, "", toSearch(state, model) || location.pathname);
  }

  function notes() {
    const metric = metricOf(state.metric);
    const results = model.rows.flatMap((row) => Object.values(row.results));
    const lines = [];
    if (resultsError) {
      lines.push(`${resultsError.message}; the table lists the architectures only.`);
    }
    if (metric) {
      lines.push([
        `Values are ${metric.name}`,
        metric.better ? ` (${metric.better} is better)` : "",
        results.some((r) => r.runs >= 2) ? ", mean ± standard deviation over runs" : "",
        metric.better ? "; bars run from 0 to 1." : ".",
      ].join(""));
    }
    lines.push([
      "— not run · n/a not defined for the task",
      results.some(isDegenerate) ? " · † no positive predictions (precision and recall are 0)" : "",
    ].join(""));
    for (const t of model.tasks) if (t.note) lines.push(`* ${t.short}: ${t.note}`);
    $("notes").replaceChildren(...lines.map((line) => h("p", { class: "table-note" }, line)));
  }

  function setSort(key) {
    state.sort = nextSort(state.sort, key, metricOf(state.metric));
    reorder();
  }

  // `reveal` is for a deep link or an "adapted from" link: the row always ends up open,
  // visible, scrolled to and focused. A plain click just toggles.
  function setOpen(name, { reveal = false } = {}) {
    const target = state.open === name && !reveal ? null : name;
    if (state.open) rowEls.get(state.open).toggle.setAttribute("aria-expanded", "false");
    state.open = target;
    if (!target) return refresh();

    const els = rowEls.get(target);
    const row = model.rows.find((r) => r.name === target);
    if (!els.panel) {
      els.panel = h("tr", { class: "panel-row", id: `panel-${target}` },
        h("td", { colspan: headers.length }, panelFor(row, model, (other) => setOpen(other, { reveal: true }))));
      els.tr.after(els.panel);
      els.toggle.setAttribute("aria-controls", els.panel.id);
    }
    els.toggle.setAttribute("aria-expanded", "true");
    if (reveal && !matches(row, state)) {
      state.q = "";
      state.family = "";
      $("q").value = "";
      familyPills.set("");
    }
    refresh();
    if (reveal) {
      const smooth = !matchMedia("(prefers-reduced-motion: reduce)").matches;
      els.tr.scrollIntoView({ block: "start", behavior: smooth ? "smooth" : "auto" });
      els.toggle.focus({ preventScroll: true });
    }
  }

  $("q").addEventListener("input", (event) => { state.q = event.target.value; refresh(); });

  fillCells();
  notes();
  reorder();
  if (state.open) setOpen(state.open, { reveal: true });
  document.documentElement.dataset.ready = "true";
}

/**
 * Toggle buttons, one pressed at a time; `set` presses the one with that id and releases
 * the rest. Options carrying a `group` are laid out as one labelled row per group.
 */
function pills(container, options, onPick) {
  const buttons = new Map(options.map((o) => [o.id, h("button", {
    class: "filter-btn", type: "button", title: o.title, "aria-pressed": "false", onclick: () => onPick(o.id),
  }, o.label)]));
  const groups = new Map();
  for (const o of options) {
    if (!groups.has(o.group)) groups.set(o.group, []);
    groups.get(o.group).push(buttons.get(o.id));
  }
  if (groups.size === 1 && groups.has(undefined)) container.replaceChildren(...buttons.values());
  else {
    container.replaceChildren(...[...groups].map(([label, row]) => h("div", { class: "controls" },
      h("span", { class: "field" }, label),
      h("div", { class: "filter-group", role: "group", "aria-label": `${label} metric` }, row))));
  }
  return {
    set(id) {
      for (const [key, button] of buttons) {
        button.setAttribute("aria-pressed", String(key === id));
        button.classList.toggle("active", key === id);
      }
    },
  };
}

/** Kit version, commit and results date under the hero links. */
function versionLine(p) {
  const kit = p.registryKit ?? p.resultsKit;
  return [
    kit ? h("a", { class: "vt", href: "https://github.com/stevenah/deepecg-kit/releases" }, `v${kit}`) : null,
    p.registrySha ? h("span", { class: "vs" }, p.registrySha) : null,
    p.generated ? h("span", { class: "vs" }, `results ${p.generated.slice(0, 10)}`) : null,
  ].filter(Boolean);
}

function provenanceLine(p) {
  const parts = [];
  if (p.nRuns != null) {
    parts.push("Results from ", h("b", {}, plural(p.nRuns, "run")));
    if (p.resultsKit) parts.push(" with deepecg-kit ", h("b", {}, p.resultsKit));
    if (p.generated) parts.push(", generated ", h("b", {}, p.generated.slice(0, 10)));
    parts.push(". ");
  }
  if (p.registryKit) {
    parts.push("Parameter counts from deepecg-kit ", h("b", {}, p.registryKit));
    if (p.registrySha) parts.push(" (", h("code", {}, p.registrySha), ")");
    parts.push(".");
  }
  return parts;
}

/** The Reference cell: the paper, cited short, over a link to its code. */
function referenceOf(row) {
  const cite = citation(row.paper);
  if (!cite && !row.codeUrl) {
    return [h("span", { class: "muted", "aria-hidden": "true" }, "—"), hidden("no published reference")];
  }
  return [
    cite ? (row.paper.url ? h("a", { href: row.paper.url, rel: "noopener", title: row.paper.title }, cite) : cite) : null,
    row.codeUrl ? h("span", { class: "ref-code" }, external(row.codeUrl, "Code")) : null,
  ];
}

/** The detail for one architecture: what the model page used to hold. */
function panelFor(row, model, openOther) {
  const facts = [
    ["Registry name", h("code", {}, row.name)],
    row.className && ["Class", h("code", {}, row.className)],
    ["Input length", inputLength(row)],
    row.featureDim != null && ["Feature dimension", row.featureDim.toLocaleString("en-US")],
    row.explain && ["Explainability", capitalise(Object.keys(EXPLAIN_LABELS)
      .filter((k) => row.explain[k]).map((k) => EXPLAIN_LABELS[k]).join(", ") || "none")],
  ].filter(Boolean);
  const adapted = row.adaptedFrom && model.rows.find((r) => r.name === row.adaptedFrom);

  const about = h("div", {},
    row.description ? h("p", { class: "panel-desc" }, row.description) : null,
    h("dl", { class: "facts" }, facts.map(([k, v]) => h("div", { class: "fact" }, h("dt", {}, k), h("dd", {}, v)))),
    row.shapes.length ? [
      h("h3", {}, "Parameters"),
      h("table", { class: "mini" }, h("tbody", {}, row.shapes.map((s) => h("tr", {},
        h("th", { scope: "row" }, `${plural(s.channels, "lead")}, ${plural(s.outputs, "output")}`,
          s.tasks.length ? ` (${s.tasks.join(", ")})` : ""),
        h("td", { class: "num" }, s.params.toLocaleString("en-US")))))),
    ] : null,
    row.paper || row.codeUrl || adapted ? [
      h("h3", {}, "Source"),
      row.paper ? h("p", {},
        row.paper.url ? external(row.paper.url, row.paper.title) : row.paper.title, ". ",
        [row.paper.authors, [row.paper.venue, row.paper.year].filter(Boolean).join(", ")].filter(Boolean).join(". "), ".") : null,
      row.codeUrl ? h("p", {}, external(row.codeUrl, "Reference implementation")) : null,
      adapted ? h("p", {}, "Adapted from ", h("a", {
        href: `?model=${encodeURIComponent(adapted.name)}`,
        onclick: (event) => { event.preventDefault(); openOther(adapted.name); },
      }, adapted.title), ".") : null,
    ] : null,
    row.notes || row.deviations.length ? [
      h("h3", {}, "Implementation notes"),
      row.notes ? h("p", {}, row.notes) : null,
      row.deviations.length ? h("ul", {}, row.deviations.map((d) => h("li", {}, d))) : null,
    ] : null,
    h("p", { class: "plot-note" }, external(`${DOCS}architectures/`, "Design of each architecture in the kit documentation")));

  const measured = model.tasks.filter((t) => row.results[t.id]);
  const results = h("div", {},
    h("h3", {}, "Results"),
    measured.length
      ? measured.map((t) => taskBlock(row, t, row.results[t.id], model))
      : h("p", { class: "muted" }, "No task has been run for this architecture yet."));
  return h("div", { class: "panel" }, about, results);
}

function inputLength(row) {
  const n = (x) => x.toLocaleString("en-US");
  if (row.minInput != null && row.maxInput != null) return `${n(row.minInput)}–${n(row.maxInput)} samples`;
  if (row.minInput != null) return `at least ${n(row.minInput)} samples`;
  if (row.maxInput != null) return `at most ${n(row.maxInput)} samples`;
  return "any";
}

function taskBlock(row, task, result, model) {
  const metrics = model.metrics.filter((m) => result.metrics[m.id]?.mean != null);
  const seeds = result.seeds ?? [];
  const meta = [
    plural(result.runs ?? 1, "run"),
    seeds.length ? `seeds ${seeds.join(", ")}` : null,
    result.averaging ? `${result.averaging} averaging` : null,
  ].filter(Boolean).join(" · ");
  const withSd = (m) => (m.n >= 2 && m.std != null ? h("span", { class: "sd" }, `± ${formatValue(m.std)}`) : null);

  const runs = Math.max(0, ...metrics.map((m) => result.metrics[m.id].values?.length ?? 0));
  const interval = model.provenance.confidence ? `${Math.round(model.provenance.confidence * 100)}% CI` : "CI";
  const perSeed = runs >= 2 ? h("details", { class: "seeds" },
    h("summary", {}, "Per-run values"),
    h("div", { class: "scroll", tabindex: "0" }, h("table", { class: "mini" },
      h("thead", {}, h("tr", {},
        h("th", { scope: "col" }, "Metric"),
        h("th", { scope: "col", class: "num" }, "Mean"),
        h("th", { scope: "col", class: "num" }, "SD"),
        h("th", { scope: "col", class: "num" }, interval),
        Array.from({ length: runs }, (_, i) =>
          h("th", { scope: "col", class: "num" }, seeds.length === runs ? `Seed ${seeds[i]}` : `Run ${i + 1}`)))),
      h("tbody", {}, metrics.map((m) => {
        const v = result.metrics[m.id];
        return h("tr", {},
          h("th", { scope: "row" }, m.label),
          h("td", { class: "num" }, formatValue(v.mean)),
          h("td", { class: "num" }, formatValue(v.std)),
          h("td", { class: "num" }, v.lo != null && v.hi != null ? `${formatValue(v.lo)}–${formatValue(v.hi)}` : ""),
          Array.from({ length: runs }, (_, i) => h("td", { class: "num" }, formatValue(v.values?.[i]))));
      }))))) : null;

  const plots = result.plots ?? [];
  return h("section", { class: "task-block" },
    h("h4", {}, task.short, h("span", {}, meta)),
    isDegenerate(result) ? h("p", { class: "flag" }, "† No positive predictions: precision and recall are 0.") : null,
    h("dl", { class: "metric-list" }, metrics.map((m) => h("div", {},
      h("dt", {}, m.label),
      h("dd", {}, formatValue(result.metrics[m.id].mean), withSd(result.metrics[m.id]))))),
    perSeed,
    plots.length ? [
      h("div", { class: "plot-grid" }, plots.map((kind) => plotCard(row, task, kind))),
      result.plot_seed != null ? h("p", { class: "plot-note" }, `Plots from the run with seed ${result.plot_seed}.`) : null,
    ] : null);
}

function plotCard(row, task, kind) {
  const label = PLOT_LABELS[kind] ?? kind.replaceAll("-", " ");
  const src = new URL(`./plots/${task.id}/${row.name}/${kind}.png`, import.meta.url).href;
  const figure = h("figure", { class: "plot-card" });
  const img = h("img", {
    src, loading: "lazy", decoding: "async", alt: `${label} for ${row.title} on ${task.short}`,
    onerror: () => figure.replaceChildren(h("figcaption", {}, `${label}: plot not available.`)),
  });
  figure.append(h("a", { href: src, title: "Open the full-size plot" }, img), h("figcaption", {}, label));
  return figure;
}

// Three-state theme toggle: dark -> light -> auto. The first paint is already right,
// because an inline script in index.html sets data-theme before the stylesheet loads.
function initTheme() {
  const KEY = "deepecg-theme";
  const order = ["dark", "light", "auto"];
  const labels = { auto: "Auto", light: "Light", dark: "Dark" };
  const glyphs = { auto: "◐", light: "☀", dark: "☾" };
  const current = () => {
    try { return localStorage.getItem(KEY) || "dark"; } catch { return "dark"; }
  };
  const apply = (mode) => {
    const root = document.documentElement;
    if (mode === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    for (const button of document.querySelectorAll("[data-theme-toggle]")) {
      button.setAttribute("aria-label", `Colour theme: ${labels[mode]}. Click to change.`);
      button.querySelector("[data-theme-glyph]").textContent = glyphs[mode];
      button.querySelector("[data-theme-label]").textContent = labels[mode];
    }
  };
  apply(current());
  for (const button of document.querySelectorAll("[data-theme-toggle]")) {
    button.addEventListener("click", () => {
      const next = order[(order.indexOf(current()) + 1) % order.length];
      try { localStorage.setItem(KEY, next); } catch { /* private mode: this page only */ }
      apply(next);
    });
  }
}

async function init() {
  initTheme();
  const status = document.getElementById("status");
  const fail = (message) => {
    status.replaceChildren(message, h("button", { type: "button", onclick: () => location.reload() }, "Retry"));
  };
  status.textContent = "Loading the benchmark data…";
  try {
    const [catalogue, registry, results] = await Promise.allSettled(DATA_FILES.map(fetchJson));
    const fatal = [catalogue, registry].find((r) => r.status === "rejected");
    if (fatal) return fail(`${fatal.reason.message}.`);
    const loaded = results.status === "fulfilled";
    mount(buildModel(catalogue.value, registry.value, loaded ? results.value : null), loaded ? null : results.reason);
  } catch (error) {
    console.error(error);
    fail(`The page could not be drawn (${error.message}).`);
  }
}

if (typeof document !== "undefined") init();
