# Secure India Dataset, Source And Methodology

## Status

**Synthetic. Not real data.** Every figure on the Secure India page is invented for product
demonstration. Nothing here is derived from CyberRakshak complaints, police systems,
government portals, NCRB publications, telecom or banking data, or any real person.

This document is the source-of-truth record required before `source_type` could ever change.

## Identity

| Field | Value |
| --- | --- |
| `dataset_id` | `secure-india-synthetic-v1` |
| `version` | `1.1.0` |
| `source_type` | `SYNTHETIC` |
| `source_label` | CyberRakshak synthetic demonstration dataset |
| `published_at` | 2026-09-10 |
| `period_end` | 2026-08-31 |
| Location | `backend/app/data/secure_india/snapshot.json` |

Version `1.1.0` replaced the hand-placed `x`/`y` pixel pairs of `1.0.0` with real `lon`/`lat`
coordinates plus a declared projection window, so map geometry is data rather than layout.

## Shape

Each of the 10 city rows carries:

```text
id                          stable identifier, kept separate from display names
city, state                 display names (not translated in the dataset)
lon, lat                    published city coordinates
zone                        an illustrative named locality used by the hot-zone cards
synthetic_population_lakh   denominator for the per-lakh view
trend_percent               illustrative period-over-period movement
counts{category}            illustrative report counts per crime category
```

Snapshot-level fields carry `projection` (the lon/lat window), `period_factors` (the fixed
multipliers behind 7D / 30D / 1Y) and `categories` (with the prevention-guide slug each
crime type links to).

## Methodology And Its Limits

- **Counts are invented.** They were chosen to be internally consistent and plausibly ordered,
  not to reflect any real distribution of cyber crime.
- **Period filters are multiplicative.** 7D and 1Y apply fixed factors (0.24 and 10.8) to the
  30D figure. This is a demonstration device: real data would have genuine per-period
  observations, and no seasonality or trend is modelled.
- **`trend_percent` is static.** It does not recompute per filter and is not derived from the
  counts. It is labelled as a synthetic trend in the UI.
- **Per-lakh is a real calculation over a fake denominator.** `value = count / synthetic_population_lakh`,
  rounded to one decimal. The denominators are approximate metropolitan figures used only so
  the toggle demonstrates genuine re-ranking; they are not census values.
- **Legend bins are derived, not fixed.** Bin width is computed from the maximum value in the
  current selection and rounded to a readable step, so the legend always matches what is drawn.
- **Coordinates are city points, not boundaries.** The map is a proportional-symbol map. It
  does not show police jurisdictions, administrative boundaries, or where any incident occurred.
- **The national outline is a simplified silhouette** projected from the same lon/lat window.
  It is a visual frame for the city markers, not a survey-accurate or authoritative boundary,
  and carries no claim about any border.

## Privacy Position

Secure India never reads citizen data. `SecureIndiaService` has no repository and no database
access at all, so complaint rows, reporter profiles, complaint locations and evidence cannot
reach the public map even though they exist in the same application. This is a structural
guarantee, not a filtering convention.

A filter selection is a query over synthetic aggregates. It is never consent to publish or
search any citizen's reported location.

## Before Using A Real Source

`source_type` must stay `SYNTHETIC` until all of the following are documented:

1. licence and permitted use of the source;
2. required attribution text;
3. jurisdiction and geographic coverage;
4. publication cadence and freshness expectations;
5. every transformation applied between the source and the served aggregate;
6. a minimum cell size and suppression rule, so small counts cannot re-identify anyone;
7. known limitations and the correct way to describe the figures to citizens.

If real complaint data is ever aggregated for this page, a separate consent, aggregation,
privacy and data-governance contract is required first, per `08-SECURITY.md`.

## Disclosure In The Product

The synthetic status is surfaced at four levels, and none of them may be removed:

- the hero carries a **Synthetic demonstration data** flag;
- a dataset note above the map repeats it with version and period;
- the map carries its own disclaimer about markers and boundaries;
- a **Dataset and methodology** disclosure exposes the methodology string, dataset id, version
  and publication date directly from the API response.

The API mirrors this: every `summary` and `metadata` response carries `source_type`,
`source_label`, `version`, `period_end` and `methodology`.
