// The page's pure logic, run with Node's built-in test runner: `node --test tools/tests/app.test.mjs`.
// No packages. site/app.js only touches the DOM when there is a document, so it imports here.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  barFraction, bestByTask, buildModel, cellFor, citation, formatParams, formatValue, isDegenerate,
  matches, nextSort, parseState, sortForMetric, sortRows, toSearch,
} from "../../site/app.js";

const load = (name) => JSON.parse(readFileSync(new URL(`../../site/data/${name}.json`, import.meta.url), "utf8"));

// A small site: three architectures, two tasks, one metric of each direction.
const catalogue = {
  families: [{ id: "base", label: "Baseline" }, { id: "cnn", label: "Convolutional" }],
  tasks: [
    { id: "multi", dataset: "ds-multi", short: "Multi", input_channels: 12, output_size: 5 },
    { id: "binary", dataset: "ds-binary", short: "Binary", input_channels: 1, output_size: 1 },
  ],
  metrics: [
    { id: "f1", label: "F1", name: "F1", better: "higher", group: null },
    { id: "accuracy", label: "Acc.", name: "Accuracy", better: "higher", group: null },
    { id: "ece", label: "ECE", name: "ECE", better: "lower", group: "calibration" },
    { id: "temperature", label: "T", name: "Temperature", better: null, group: "calibration" },
  ],
  models: [
    { name: "big", family: "cnn", summary: "A large residual network.", paper: { year: 2016, title: "Deep Residual Learning", authors: "He" } },
    { name: "small", family: "cnn", summary: "A small network." },
    { name: "linear", family: "base", summary: "A linear baseline." },
  ],
};
const probe = (params) => ({ status: "ok", params_trainable: params, feature_dim: 8 });
const registry = {
  meta: { kit_version: "1.0.0", kit_git_sha: "abc", canonical_probe: "12x5",
    probes: { "12x5": { input_channels: 12, output_size: 5 }, "1x1": { input_channels: 1, output_size: 1 } } },
  constants: { lower_is_better: ["ece", "nll"] },
  models: {
    big: { registry_name: "big", display_name: "BigNet", class: "Big", description: "from the registry", probes: { "12x5": probe(9_000_000), "1x1": probe(8_900_000) } },
    small: { registry_name: "small", display_name: "SmallNet", class: "Small", description: "", probes: { "12x5": probe(100_000), "1x1": probe(90_000) } },
    linear: { registry_name: "linear", display_name: "Linear", class: "Linear", description: "", probes: { "12x5": probe(5_000_000), "1x1": probe(1_000) } },
    fresh: { registry_name: "fresh", display_name: null, class: "Fresh", description: "Registered upstream, not yet described.", probes: { "12x5": probe(42), "1x1": probe(41) } },
  },
};
const metric = (mean, extra = {}) => ({ n: 1, mean, std: null, lo: null, hi: null, values: [mean], ...extra });
const results = {
  generated: "2026-01-02T03:04:05Z", kit_version: "0.9.0", n_runs: 4, confidence_level: 0.95,
  rows: [
    { model: "big", task: "multi", runs: 1, metrics: { f1: metric(0.7), ece: metric(0.05), temperature: metric(1.4) } },
    { model: "small", task: "multi", runs: 1, metrics: { f1: metric(0.6), ece: metric(0.02) } },
    { model: "big", task: "binary", runs: 1, metrics: { f1: metric(0), accuracy: metric(0.65), precision: metric(0), recall: metric(0) } },
    { model: "small", task: "binary", runs: 1, metrics: { f1: metric(0.9), accuracy: metric(0.95), precision: metric(0.9), recall: metric(0.9) } },
    { model: "ghost", task: "multi", runs: 1, metrics: { f1: metric(1) } },
    { model: "big", task: "retired", runs: 1, metrics: { f1: metric(1) } },
  ],
};
const model = buildModel(catalogue, registry, results);
const row = (name) => model.rows.find((r) => r.name === name);
const names = (rows) => rows.map((r) => r.name);
const metricOf = (id) => model.metrics.find((m) => m.id === id);

test("rows come from the registry, in family then parameter order", () => {
  assert.deepEqual(names(model.rows), ["linear", "small", "big", "fresh"]);
  assert.equal(row("big").title, "BigNet");
  assert.equal(row("big").familyLabel, "Convolutional");
  assert.equal(row("big").year, 2016);
});

test("an architecture without a catalogue entry is drawn from the registry", () => {
  const fresh = row("fresh");
  assert.equal(fresh.title, "fresh");
  assert.equal(fresh.description, "Registered upstream, not yet described.");
  assert.equal(fresh.familyLabel, null);
  assert.equal(fresh.explain, null);
});

test("results for unknown architectures or tasks are left out of the counts", () => {
  assert.deepEqual(model.counts, { models: 4, tasks: 2, measured: 4, total: 8 });
});

test("parameter counts are listed per input shape with the tasks that use it", () => {
  assert.deepEqual(row("big").shapes, [
    { key: "12x5", channels: 12, outputs: 5, params: 9_000_000, tasks: ["Multi"] },
    { key: "1x1", channels: 1, outputs: 1, params: 8_900_000, tasks: ["Binary"] },
  ]);
});

test("only metrics that occur are offered; unknown ones take their direction from the registry", () => {
  assert.deepEqual(model.metrics.map((m) => m.id), ["f1", "accuracy", "ece", "temperature", "precision", "recall"]);
  assert.equal(model.defaultMetric, "f1");
  const withUnknown = buildModel(catalogue, registry, { rows: [{ model: "big", task: "multi", metrics: { nll: metric(1) } }] });
  assert.deepEqual(withUnknown.metrics, [{ id: "nll", label: "nll", name: "nll", better: "lower", group: null }]);
  assert.equal(withUnknown.defaultMetric, "nll");
});

test("without results the table still lists every architecture", () => {
  const bare = buildModel(catalogue, registry, null);
  assert.equal(bare.rows.length, 4);
  assert.deepEqual(bare.metrics, []);
  assert.equal(bare.defaultMetric, null);
  assert.equal(cellFor(bare.rows[0], "multi", null).state, "none");
});

test("a cell is a value, not applicable, or not run", () => {
  assert.equal(cellFor(row("big"), "multi", "f1").mean, 0.7);
  assert.equal(cellFor(row("big"), "multi", "accuracy").state, "na", "run, but the metric is not defined there");
  assert.equal(cellFor(row("linear"), "multi", "f1").state, "none", "never run");
  assert.equal(cellFor(row("big"), "binary", "accuracy").degenerate, true);
  assert.equal(cellFor(row("small"), "binary", "accuracy").degenerate, false);
});

test("a run with no positive predictions is recognised from precision and recall", () => {
  assert.equal(isDegenerate(row("big").results.binary), true);
  assert.equal(isDegenerate(row("big").results.multi), false, "no precision or recall recorded");
  assert.equal(isDegenerate(undefined), false);
});

test("the best value follows the metric's direction and needs two values to compare", () => {
  assert.deepEqual([...bestByTask(model.rows, model.tasks, metricOf("f1"))], [["multi", 0.7], ["binary", 0.9]]);
  assert.deepEqual([...bestByTask(model.rows, model.tasks, metricOf("ece"))], [["multi", 0.02]]);
  assert.equal(bestByTask(model.rows, model.tasks, metricOf("temperature")).size, 0, "no direction, no best");
});

test("sorting puts empty cells last in both directions", () => {
  assert.deepEqual(names(sortRows(model.rows, { key: "multi", dir: "desc" }, "f1")), ["big", "small", "linear", "fresh"]);
  assert.deepEqual(names(sortRows(model.rows, { key: "multi", dir: "asc" }, "f1")), ["small", "big", "linear", "fresh"]);
  assert.deepEqual(names(sortRows(model.rows, { key: "params", dir: "desc" }, "f1")), ["big", "linear", "small", "fresh"]);
  assert.deepEqual(names(sortRows(model.rows, { key: "name", dir: "asc" }, "f1")), ["big", "fresh", "linear", "small"]);
  assert.deepEqual(names(sortRows(model.rows, null, "f1")), ["linear", "small", "big", "fresh"]);
  assert.deepEqual(names(sortRows(model.rows, { key: "binary", dir: "desc" }, "accuracy")), ["small", "big", "linear", "fresh"]);
});

test("a header cycles best-first, reversed, default", () => {
  const f1 = metricOf("f1");
  const ece = metricOf("ece");
  assert.deepEqual(nextSort(null, "multi", f1), { key: "multi", dir: "desc" });
  assert.deepEqual(nextSort({ key: "multi", dir: "desc" }, "multi", f1), { key: "multi", dir: "asc" });
  assert.equal(nextSort({ key: "multi", dir: "asc" }, "multi", f1), null);
  assert.deepEqual(nextSort(null, "multi", ece), { key: "multi", dir: "asc" }, "lower is better: smallest first");
  assert.deepEqual(nextSort(null, "name", f1), { key: "name", dir: "asc" });
  assert.deepEqual(nextSort({ key: "name", dir: "asc" }, "multi", f1), { key: "multi", dir: "desc" }, "a new column starts over");
});

test("a column sorted best-first stays best-first when the metric's direction changes", () => {
  const [f1, accuracy, ece] = ["f1", "accuracy", "ece"].map(metricOf);
  const bestF1 = { key: "multi", dir: "desc" };
  assert.deepEqual(sortForMetric(bestF1, f1, ece), { key: "multi", dir: "asc" });
  assert.deepEqual(sortForMetric({ key: "multi", dir: "asc" }, ece, f1), bestF1);
  assert.equal(sortForMetric(bestF1, f1, accuracy), bestF1, "same direction: unchanged");
  assert.deepEqual(sortForMetric({ key: "params", dir: "asc" }, f1, ece), { key: "params", dir: "asc" });
  assert.equal(sortForMetric(null, f1, ece), null);
});

test("family and search filters combine; every search word must match", () => {
  assert.deepEqual(names(model.rows.filter((r) => matches(r, { family: "cnn", q: "" }))), ["small", "big"]);
  assert.deepEqual(names(model.rows.filter((r) => matches(r, { family: "", q: "RESIDUAL he" }))), ["big"]);
  assert.deepEqual(names(model.rows.filter((r) => matches(r, { family: "base", q: "residual" }))), []);
  assert.equal(model.rows.filter((r) => matches(r, { family: "", q: "   " })).length, 4);
});

test("numbers are formatted as the article formats them", () => {
  assert.equal(formatValue(0.70594), "0.706");
  assert.equal(formatValue(0), "0.000", "a measured zero is a number, not a blank");
  assert.equal(formatValue(null), "");
  assert.equal(formatParams(8_739_973), "8.740");
  assert.equal(formatParams(10_005), "0.010");
  assert.equal(formatParams(null), "");
});

test("a paper is cited by its first author, or both, and its year", () => {
  assert.equal(citation({ authors: "Hannun, Rajpurkar, Haghpanahi", year: 2019 }), "Hannun et al. 2019");
  assert.equal(citation({ authors: "Hochreiter, Schmidhuber", year: 1997 }), "Hochreiter and Schmidhuber 1997");
  assert.equal(citation({ authors: "Ismail Fawaz, Lucas, Forestier", year: 2020 }), "Ismail Fawaz et al. 2020");
  assert.equal(citation({ authors: "He", year: 2016 }), "He 2016");
  assert.equal(citation({ title: "An unattributed report" }), "An unattributed report");
  assert.equal(citation(null), null);
});

test("bars run from 0 to 1 and are absent for a metric without a direction", () => {
  assert.equal(barFraction(0.7, metricOf("f1")), 0.7);
  assert.equal(barFraction(-0.2, metricOf("f1")), 0);
  assert.equal(barFraction(1.4, metricOf("f1")), 1);
  assert.equal(barFraction(1.4, metricOf("temperature")), null);
});

test("state round-trips through the URL and defaults stay out of it", () => {
  const plain = parseState("", model);
  assert.deepEqual(plain, { metric: "f1", sort: null, family: "", q: "", open: null });
  assert.equal(toSearch(plain, model), "");
  const state = { metric: "ece", sort: { key: "multi", dir: "asc" }, family: "cnn", q: "res net", open: "big" };
  assert.deepEqual(parseState(toSearch(state, model), model), state);
});

test("unrecognised URL parameters fall back to defaults", () => {
  const state = parseState("?metric=bogus&sort=nope&family=x&model=ghost&dir=sideways", model);
  assert.deepEqual(state, { metric: "f1", sort: null, family: "", q: "", open: null });
});

test("the committed data files build a consistent page", () => {
  const live = buildModel(load("catalogue"), load("registry"), load("results"));
  const published = load("results").rows.length;
  assert.equal(live.counts.models, Object.keys(load("registry").models).length);
  assert.equal(live.counts.measured, published, "every published pair is shown");
  assert.equal(live.counts.total, live.counts.models * live.counts.tasks);
  assert.ok(live.rows.every((r) => r.family && r.summary), "every architecture has a family and a summary");
  assert.ok(live.rows.every((r) => r.shapes.length === Object.keys(load("registry").meta.probes).length));
  assert.ok(live.metrics.every((m) => m.label !== m.id), "every metric in the results has a catalogue label");
  for (let i = 1; i < live.rows.length; i += 1) {
    const [a, b] = [live.rows[i - 1], live.rows[i]];
    assert.ok(a.familyIndex < b.familyIndex || (a.familyIndex === b.familyIndex && a.params <= b.params),
      `${a.name} and ${b.name} are out of the default order`);
  }
});
