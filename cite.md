---
layout: default
title: How to cite
permalink: /cite/
---
{%- assign ev = site.data.generated.evidence -%}
<header class="hero"><div class="wrap">
<h1>How to cite</h1>
</div></header>

<div class="wrap-narrow prose" style="padding:32px 24px 48px">

## Citing the library

Cite the DeepECG-Kit paper and the repository. See
<a href="{{ site.kit_repo }}">{{ site.kit_repo }}</a> for the current reference.

## Citing results from this site

The current snapshot is **`{{ ev.snapshot_id }}`**, status **{{ ev.snapshot_status }}**,
generated {{ ev.generated_utc }} from deepecgkit {{ ev.kit_version }}.

<div class="callout bad">
<h3>Do not cite this snapshot as a benchmark result</h3>
<p>Its status is <b>{{ ev.snapshot_status }}</b>: every cell is a single run, with no replicate
variance, no calibration metrics and an unrecorded averaging mode. Cite the software, and cite
the snapshot only to say <em>which numbers you looked at</em> &mdash; not as evidence that one
architecture outperforms another.</p>
</div>

Once a seeded snapshot exists, cite it by id and link its immutable directory:

```
DeepECG-Bench snapshot <id>, generated <date> from deepecgkit <version> (<commit>).
{{ site.url }}{{ site.baseurl }}/snapshots/<id>/
```

Every snapshot keeps a permanent URL and a `CHECKSUMS.sha256`, so a reader can verify that the
CSVs they downloaded are the ones the page described.

## Citing the dataset catalogue

Dataset-side provenance lives in [ECGBench](https://vajira.info/ECGBench/), which catalogues the
source datasets these tasks are built from. Cite it for dataset properties and splits.

</div>
