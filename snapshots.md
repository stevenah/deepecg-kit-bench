---
layout: default
title: Snapshots
permalink: /snapshots/
---
<header class="hero"><div class="wrap">
<h1>Snapshots</h1>
</div></header>

<div class="wrap" style="padding-top:28px">
<section>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Snapshot</th><th>Status</th><th>Generated</th><th>Library</th><th>Replicates</th><th>Files</th></tr></thead>
      <tbody>
      {% for s in site.snapshots %}
        <tr>
          <td><a class="row-name" href="{{ s.url | relative_url }}">{{ s.snapshot_id }}</a>
            <span class="row-sub">{{ s.label }}</span></td>
          <td><span class="chip chip-warn">{{ s.status }}</span></td>
          <td class="muted nowrap">{{ s.generated_utc }}</td>
          <td class="muted nowrap">{{ s.kit_version }}</td>
          <td class="muted">{{ s.replicate_kind }}</td>
          <td><a href="{{ '/results/snapshots/' | append: s.snapshot_id | append: '/' | relative_url }}">CSVs</a></td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
  <p class="muted" style="font-size:.85rem;margin-top:12px">
    A missing recent row is itself informative: it means nobody has published results lately.
    Staleness is also computed in your browser from the snapshot timestamp, so this page stays
    honest even if the site is never rebuilt.
  </p>
</section>
</div>
