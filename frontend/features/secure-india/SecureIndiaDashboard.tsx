"use client";

import Link from "next/link";
import {useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore} from "react";
import {useLocale, useTranslations} from "next-intl";
import {ArrowRight, BarChart3, BookOpen, ChevronRight, Database, Flame, MapPinned, PhoneCall, RotateCcw, Search, ShieldAlert, TrendingDown, TrendingUp} from "lucide-react";

import {secureIndiaApi, type SecureIndiaRegion, type SecureIndiaSummary} from "@/lib/api/secure-india";

const crimeTypes = ["all", "financial", "commerce", "identity", "harassment", "other"] as const;
const periods = ["7d", "30d", "1y"] as const;
const views = ["count", "per_lakh"] as const;

type Period = (typeof periods)[number];
type View = (typeof views)[number];
type Filters = {city: string; crimeType: string; period: Period; state: string; view: View};

const defaultFilters: Filters = {city: "all", crimeType: "all", period: "30d", state: "all", view: "count"};

// Sequential ramp shared by the map, the legend and the card meters. Colour is
// never the only carrier of meaning: every region also has a proportional
// radius, a rank number and an exact value in the ranked table.
const bucketColors = ["#fbe3d3", "#f7bf9a", "#ef8f63", "#d9533a", "#9e1b18"];

// National outline projected from the same lon/lat window the API uses, so the
// silhouette and the plotted cities share one coordinate system.
const indiaOutline = "M22.11 5.59 L23.43 3.5 L26.73 0.7 L30.69 1.05 L33.99 2.45 L35.64 5.59 L37.62 7.34 L38.61 10.49 L37.29 12.94 L38.28 15.03 L40.92 18.18 L44.22 20.28 L47.52 20.63 L50.5 22.73 L53.8 24.48 L56.77 25.87 L60.4 27.62 L63.37 28.32 L67.0 29.02 L68.32 29.02 L69.97 30.42 L70.63 31.82 L70.96 32.52 L72.94 32.87 L75.58 32.52 L79.21 32.87 L80.86 30.77 L83.17 29.02 L86.8 26.57 L90.43 27.62 L93.73 28.32 L96.7 27.27 L98.68 28.32 L98.35 31.12 L96.04 32.17 L94.06 33.92 L91.42 33.57 L89.77 36.01 L89.11 38.46 L88.12 41.26 L85.81 42.66 L84.49 44.76 L84.82 47.55 L83.17 49.3 L82.84 51.05 L81.52 43.71 L82.51 40.91 L77.56 38.46 L73.6 38.11 L70.63 38.46 L67.99 40.91 L69.97 41.96 L68.32 45.45 L70.63 48.95 L68.32 50.7 L65.02 51.05 L64.03 52.45 L62.71 54.55 L60.73 56.29 L58.42 58.04 L56.44 59.79 L54.13 62.24 L51.16 64.69 L48.84 67.13 L46.53 68.88 L44.55 70.28 L43.23 71.33 L42.57 73.43 L42.9 76.22 L43.4 79.02 L42.9 81.82 L41.25 84.27 L40.59 86.71 L39.6 88.81 L38.61 90.56 L36.63 93.01 L34.98 94.76 L34.32 96.85 L33.0 98.25 L31.68 97.55 L30.69 95.45 L29.37 93.01 L28.05 90.21 L27.06 87.41 L25.41 84.97 L23.76 81.82 L22.77 79.37 L21.78 76.22 L20.79 73.08 L19.8 70.98 L18.81 68.53 L18.15 65.73 L17.49 62.24 L17.16 59.44 L17.16 56.64 L17.82 54.2 L16.83 51.75 L15.51 50.7 L13.2 53.15 L10.56 53.85 L7.92 52.8 L5.61 50.35 L3.96 48.25 L2.31 46.15 L2.97 44.06 L5.28 42.66 L8.25 41.96 L10.23 37.41 L11.22 33.57 L13.53 30.07 L16.5 27.97 L19.14 23.78 L21.45 20.98 L23.43 18.18 L25.41 14.69 L27.06 12.59 L24.42 9.79 Z";

function readFiltersFromSearch(search: string): Filters {
  const params = new URLSearchParams(search);
  const period = params.get("period");
  const view = params.get("view");
  const crimeType = params.get("crime_type");
  return {
    city: params.get("city") ?? defaultFilters.city,
    crimeType: crimeTypes.includes(crimeType as (typeof crimeTypes)[number]) ? (crimeType as string) : defaultFilters.crimeType,
    period: periods.includes(period as Period) ? (period as Period) : defaultFilters.period,
    state: params.get("state") ?? defaultFilters.state,
    view: views.includes(view as View) ? (view as View) : defaultFilters.view
  };
}

function toSearchParams(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.crimeType !== defaultFilters.crimeType) params.set("crime_type", filters.crimeType);
  if (filters.state !== defaultFilters.state) params.set("state", filters.state);
  if (filters.city !== defaultFilters.city) params.set("city", filters.city);
  if (filters.period !== defaultFilters.period) params.set("period", filters.period);
  if (filters.view !== defaultFilters.view) params.set("view", filters.view);
  return params;
}

// The query string is the single source of truth for filter state, so a view can
// be shared, bookmarked and restored. It is consumed through useSyncExternalStore
// rather than an effect: the server snapshot is the documented default view, so
// server and client markup always agree and no hydration mismatch is possible.
const filterListeners = new Set<() => void>();
let cachedSearch: string | null = null;
let cachedFilters: Filters = defaultFilters;

function subscribeToFilters(onChange: () => void) {
  filterListeners.add(onChange);
  window.addEventListener("popstate", onChange);
  return () => {
    filterListeners.delete(onChange);
    window.removeEventListener("popstate", onChange);
  };
}

// Must stay referentially stable between renders or React will loop.
function getFilterSnapshot(): Filters {
  if (window.location.search !== cachedSearch) {
    cachedSearch = window.location.search;
    cachedFilters = readFiltersFromSearch(cachedSearch);
  }
  return cachedFilters;
}

function getServerFilterSnapshot(): Filters {
  return defaultFilters;
}

function writeFilters(filters: Filters) {
  const params = toSearchParams(filters);
  // replaceState keeps filter tweaks out of the back-button history while still
  // producing a copyable URL; history.replaceState does not emit popstate itself.
  window.history.replaceState(null, "", window.location.pathname + (params.toString() ? "?" + params.toString() : ""));
  filterListeners.forEach((listener) => listener());
}

export function SecureIndiaDashboard() {
  const t = useTranslations("secureIndia");
  const locale = useLocale();
  const filters = useSyncExternalStore(subscribeToFilters, getFilterSnapshot, getServerFilterSnapshot);
  const [attempt, setAttempt] = useState(0);
  const [response, setResponse] = useState<{error: boolean; key: string; summary: SecureIndiaSummary | null}>({error: false, key: "", summary: null});
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const mapRef = useRef<HTMLDivElement | null>(null);

  const queryString = useMemo(
    () => new URLSearchParams({city: filters.city, crime_type: filters.crimeType, period: filters.period, state: filters.state, view: filters.view}).toString(),
    [filters]
  );
  // Loading is derived from "the answer on screen is not the answer for the
  // filters currently selected", so no effect has to synchronously set it.
  const requestKey = queryString + "#" + attempt;
  const loading = response.key !== requestKey;

  useEffect(() => {
    const controller = new AbortController();
    // Coalesce rapid filter changes into a single request. This also absorbs the
    // one-frame settle on a deep-linked load, where the first client render still
    // holds the default server snapshot: without it that default view would be
    // fetched and immediately aborted on every shared link.
    const timer = window.setTimeout(() => {
      secureIndiaApi.summary(new URLSearchParams(queryString), {signal: controller.signal}).then((result) => {
        if (controller.signal.aborted) return;
        // A failed load clears the previous snapshot: stale figures must never be
        // presented as the current answer for the selected filters.
        setResponse(result.ok ? {error: false, key: requestKey, summary: result.data} : {error: true, key: requestKey, summary: null});
      });
    }, 60);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [queryString, requestKey]);

  const summary = response.summary;
  const error = response.error;
  const update = useCallback((patch: Partial<Filters>) => writeFilters({...getFilterSnapshot(), ...patch}), []);
  const cities = useMemo(() => summary?.available_cities ?? [], [summary]);
  const regions = useMemo(() => summary?.map_regions ?? [], [summary]);
  const selected = regions.find((item) => item.id === selectedRegion) ?? regions[0];
  const active = regions.find((item) => item.id === hovered) ?? null;
  const maxValue = Math.max(1, ...regions.map((item) => item.value));
  const isFiltered = filters.crimeType !== "all" || filters.state !== "all" || filters.city !== "all" || filters.period !== "30d" || filters.view !== "count";

  const formatValue = useCallback(
    (value: number) => (filters.view === "per_lakh" ? value.toFixed(1) : Math.round(value).toLocaleString("en-IN")),
    [filters.view]
  );

  const regionFacts = useCallback(
    (region: SecureIndiaRegion) => t("regionAria", {city: region.city, state: region.state, value: formatValue(region.value), view: t("views." + filters.view)}),
    [filters.view, formatValue, t]
  );

  function focusMap(id: string) {
    setSelectedRegion(id);
    mapRef.current?.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center"});
  }

  return (
    <main className="secure-india-page">
      <header className="secure-india-live-hero">
        <div className="shell-container">
          <p className="secure-india-kicker"><MapPinned aria-hidden="true" size={15} />{t("kicker")}</p>
          <h1>{t("title")}</h1>
          <p className="secure-india-subtitle">{t("subtitle")}</p>
          <p>{t("copy")}</p>
          <div className="secure-india-source-flag">
            <Database aria-hidden="true" size={16} />
            <span><strong>{t("syntheticLabel")}</strong>{t("syntheticHeroNote")}</span>
          </div>
          <dl className="secure-india-metrics" aria-label={t("summaryLabel")}>
            {(summary?.metrics ?? [{id: "reports", value: 0}, {id: "regions", value: 0}, {id: "rising", value: 0}, {id: "categories", value: 0}]).map((metric) => (
              <div key={metric.id}>
                <dt>{t("metrics." + metric.id)}</dt>
                <dd>{loading && !summary ? "—" : metric.value.toLocaleString("en-IN")}</dd>
              </div>
            ))}
          </dl>
        </div>
      </header>

      <div className="shell-container secure-india-content">
        <section className="secure-india-filter-panel" aria-label={t("filters.title")}>
          <label>
            {t("filters.crimeType")}
            <select onChange={(event) => update({crimeType: event.target.value})} value={filters.crimeType}>
              {crimeTypes.map((item) => <option key={item} value={item}>{t("crimeTypes." + item)}</option>)}
            </select>
          </label>
          <label>
            {t("filters.state")}
            <select onChange={(event) => update({city: "all", state: event.target.value})} value={filters.state}>
              <option value="all">{t("filters.allIndia")}</option>
              {summary?.available_states.map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label>
            {t("filters.city")}
            <select disabled={cities.length === 0} onChange={(event) => update({city: event.target.value})} value={filters.city}>
              <option value="all">{t("filters.allCities")}</option>
              {cities.map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <fieldset>
            <legend>{t("filters.timeRange")}</legend>
            <div className="secure-india-segmented">
              {periods.map((item) => (
                <button aria-pressed={filters.period === item} key={item} onClick={() => update({period: item})} type="button">{t("periods." + item)}</button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>{t("filters.viewAs")}</legend>
            <div className="secure-india-segmented">
              {views.map((item) => (
                <button aria-pressed={filters.view === item} key={item} onClick={() => update({view: item})} type="button">{t("views." + item)}</button>
              ))}
            </div>
          </fieldset>
          <button className="secure-india-reset" disabled={!isFiltered} onClick={() => writeFilters(defaultFilters)} type="button">
            <RotateCcw aria-hidden="true" size={13} />{t("filters.reset")}
          </button>
        </section>

        {error ? (
          <section className="secure-india-state" role="alert">
            <ShieldAlert aria-hidden="true" />
            <div>
              <h2>{t("errorTitle")}</h2>
              <p>{t("errorCopy")}</p>
              <button onClick={() => setAttempt((current) => current + 1)} type="button">{t("retry")}</button>
            </div>
          </section>
        ) : null}
        {loading && !summary ? <section className="secure-india-map-skeleton" aria-label={t("loading")} /> : null}

        {summary ? (
          <>
            <section className="secure-india-data-note">
              <strong>{t("syntheticLabel")}</strong>
              <span>{t("datasetNote", {periodEnd: summary.source.period_end, version: summary.source.version})}</span>
            </section>

            <div className="secure-india-main-grid">
              <section aria-labelledby="map-title" className={"secure-india-map-card" + (loading ? " is-loading" : "")}>
                <div className="secure-india-section-head">
                  <div>
                    <p className="secure-india-breadcrumb">
                      {filters.state === "all" ? t("filters.allIndia") : filters.state}
                      {filters.city === "all" ? null : <><ChevronRight aria-hidden="true" size={11} />{filters.city}</>}
                    </p>
                    <h2 id="map-title">{t("mapTitle")}</h2>
                  </div>
                  <span>{t("mapScale", {view: t("views." + filters.view)})}</span>
                </div>

                <div className="secure-india-map-layout">
                  <div className="secure-india-map-frame" ref={mapRef}>
                    <svg aria-label={t("mapAria")} className="secure-india-map" role="img" viewBox="0 0 100 105">
                      <path className="secure-india-map-outline" d={indiaOutline} />
                      {regions.map((region, index) => {
                        // Radius is proportional to the square root of the value so
                        // that circle AREA, not radius, encodes magnitude.
                        const radius = 2.5 + Math.sqrt(region.value / maxValue) * 2.7;
                        const isActive = selected?.id === region.id;
                        return (
                          <g
                            aria-label={regionFacts(region)}
                            className={"secure-india-marker" + (isActive ? " is-active" : "")}
                            key={region.id}
                            onBlur={() => setHovered(null)}
                            onClick={() => setSelectedRegion(region.id)}
                            onFocus={() => setHovered(region.id)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                setSelectedRegion(region.id);
                              }
                            }}
                            onMouseEnter={() => setHovered(region.id)}
                            onMouseLeave={() => setHovered(null)}
                            role="button"
                            tabIndex={0}
                          >
                            {isActive ? <circle className="secure-india-marker-ring" cx={region.x} cy={region.y} r={radius + 2.4} /> : null}
                            <circle cx={region.x} cy={region.y} fill={bucketColors[region.bucket] ?? bucketColors[0]} r={radius} />
                            <text x={region.x} y={region.y + 1}>{index + 1}</text>
                          </g>
                        );
                      })}
                    </svg>
                    {active ? (
                      <div className="secure-india-tooltip" style={{left: active.x + "%", top: active.y + "%"}}>
                        <strong>{active.city}</strong>
                        <span>{active.state}</span>
                        <b>{formatValue(active.value)}</b>
                        <small>{t("views." + filters.view)}</small>
                      </div>
                    ) : null}
                  </div>

                  <div className="secure-india-map-side">
                    <aside aria-live="polite" className="secure-india-map-detail">
                      {selected ? (
                        <>
                          <span>{t("selectedRegion")}</span>
                          <h3>{selected.city}</h3>
                          <p>{selected.state}</p>
                          <strong>{formatValue(selected.value)}</strong>
                          <small>{t("views." + filters.view)}</small>
                          <em className={selected.trend_percent >= 0 ? "up" : "down"}>
                            {selected.trend_percent >= 0 ? <TrendingUp aria-hidden="true" size={15} /> : <TrendingDown aria-hidden="true" size={15} />}
                            {Math.abs(selected.trend_percent)}% {t("trend")}
                          </em>
                        </>
                      ) : <p>{t("emptyMap")}</p>}
                    </aside>

                    <div className="secure-india-legend">
                      <p>{t("legendTitle", {view: t("views." + filters.view)})}</p>
                      <ul>
                        {summary.legend.map((bin) => (
                          <li key={bin.index}>
                            <span aria-hidden="true" style={{background: bucketColors[bin.index] ?? bucketColors[0]}} />
                            {bin.max === null
                              ? t("legendFrom", {min: formatValue(bin.min)})
                              : t("legendRange", {max: formatValue(bin.max), min: formatValue(bin.min)})}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                {regions.length === 0 ? <p className="secure-india-empty">{t("noDataForFilters")}</p> : null}
                <p className="secure-india-map-disclaimer">{t("mapDisclaimer")}</p>
              </section>

              <section aria-labelledby="ranking-title" className="secure-india-ranking">
                <div className="secure-india-section-head">
                  <div>
                    <p>{t("rankingEyebrow")}</p>
                    <h2 id="ranking-title">{t("rankingTitle")}</h2>
                  </div>
                  <BarChart3 aria-hidden="true" size={21} />
                </div>
                <p className="secure-india-table-note">{t("tableEquivalentNote")}</p>
                <div className="secure-india-table-wrap">
                  <table>
                    <caption>{t("rankingCaption")}</caption>
                    <thead>
                      <tr><th scope="col">{t("rank")}</th><th scope="col">{t("place")}</th><th scope="col">{t("value")}</th><th scope="col">{t("change")}</th></tr>
                    </thead>
                    <tbody>
                      {summary.rankings.map((region, index) => (
                        <tr className={selected?.id === region.id ? "is-active" : ""} key={region.id}>
                          <td><span className={"secure-india-rank" + (index < 3 ? " is-top" : "")}>{index + 1}</span></td>
                          <td>
                            <button aria-pressed={selected?.id === region.id} onClick={() => setSelectedRegion(region.id)} type="button">
                              <strong>{region.city}</strong>
                              <small>{region.state}</small>
                            </button>
                          </td>
                          <td>{formatValue(region.value)}</td>
                          <td className={region.trend_percent >= 0 ? "up" : "down"}>{region.trend_percent >= 0 ? "↑" : "↓"} {Math.abs(region.trend_percent)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>

            <section aria-labelledby="hot-zones-title" className="secure-india-hot-section">
              <div className="secure-india-section-head">
                <div>
                  <p>{t("exploreEyebrow")}</p>
                  <h2 id="hot-zones-title">{t("hotZonesTitle")}</h2>
                </div>
                <Flame aria-hidden="true" size={21} />
              </div>
              <div className="secure-india-zone-grid">
                {summary.hot_zones.map((region, index) => (
                  <button key={region.id} onClick={() => focusMap(region.id)} type="button">
                    <span>{index + 1}</span>
                    <strong>{region.zone}</strong>
                    <small>{region.city}, {region.state}</small>
                    <b>{formatValue(region.value)}</b>
                    <span className="secure-india-meter">
                      <i style={{background: bucketColors[region.bucket] ?? bucketColors[0], width: Math.max(6, (region.value / maxValue) * 100) + "%"}} />
                    </span>
                    <em>{t("inspectMap")} <ArrowRight aria-hidden="true" size={14} /></em>
                  </button>
                ))}
              </div>
            </section>

            <section aria-labelledby="hot-crimes-title" className="secure-india-hot-section">
              <div className="secure-india-section-head">
                <div>
                  <p>{t("learnEyebrow")}</p>
                  <h2 id="hot-crimes-title">{t("hotCrimesTitle")}</h2>
                </div>
                <BookOpen aria-hidden="true" size={21} />
              </div>
              <div className="secure-india-crime-grid">
                {summary.hot_crimes.map((crime) => (
                  <article key={crime.id}>
                    <span>{crime.id === "financial" ? "₹" : crime.id === "commerce" ? "B" : crime.id === "identity" ? "ID" : crime.id === "harassment" ? "!" : "?"}</span>
                    <h3>{t("crimeTypes." + crime.id)}</h3>
                    <strong>{crime.share_percent}%</strong>
                    <small>{t("shareNote")}</small>
                    <span className="secure-india-meter">
                      <i style={{background: "#c96c17", width: Math.max(4, crime.share_percent) + "%"}} />
                    </span>
                    <Link href={`/${locale}/resources`}>{t("preventionTips")} <ArrowRight aria-hidden="true" size={14} /></Link>
                  </article>
                ))}
              </div>
            </section>

            <section className="secure-india-suspect-band">
              <div>
                <Search aria-hidden="true" size={24} />
                <span><strong>{t("suspectTitle")}</strong><small>{t("suspectCopy")}</small></span>
              </div>
              <Link href={`/${locale}/suspects/search`}>{t("suspectAction")} <ArrowRight aria-hidden="true" size={16} /></Link>
            </section>

            <section className="secure-india-cta">
              <div>
                <strong>{t("reportTitle")}</strong>
                <span>{t("reportCopy")}</span>
              </div>
              <Link href={`/${locale}/report-crime`}>{t("reportAction")} <ArrowRight aria-hidden="true" size={15} /></Link>
            </section>

            <section className="secure-india-learning">
              <div>
                <BookOpen aria-hidden="true" size={20} />
                <span><strong>{t("learningTitle")}</strong><small>{t("learningCopy")}</small></span>
              </div>
              <Link href={`/${locale}/resources`}>{t("learningAction")} <ArrowRight aria-hidden="true" size={15} /></Link>
            </section>

            <p className="secure-india-helpline"><PhoneCall aria-hidden="true" size={16} />{t("helplineNote")}</p>

            <details className="secure-india-methodology">
              <summary>{t("methodologyTitle")}</summary>
              <p>{summary.source.methodology}</p>
              <dl>
                <div><dt>{t("datasetId")}</dt><dd>{summary.source.dataset_id}</dd></div>
                <div><dt>{t("datasetVersion")}</dt><dd>{summary.source.version}</dd></div>
                <div><dt>{t("published")}</dt><dd>{summary.source.published_at.slice(0, 10)}</dd></div>
              </dl>
            </details>
          </>
        ) : null}
      </div>
    </main>
  );
}
