# Benchmark Data

Peer benchmarks for German companies by NACE sector prefix.

Source: Bundesbank/ECB BACH database 2022 (Mittelstand segment).
Values are approximate medians/quartiles representative of German mid-size companies.

Files:
- `C_manufacturing.json` — NACE C: Manufacturing
- `G_wholesale_retail.json` — NACE G: Wholesale & Retail Trade

Each file contains `median`, `p25`, `p75` for each metric.
The BenchmarkStore falls back from specific NACE (e.g. C25) to prefix (C).

To add a sector: create a new JSON file following the same schema and set `nace_prefix`.
