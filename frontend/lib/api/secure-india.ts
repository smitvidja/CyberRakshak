import {apiClient, type ApiRequestOptions} from "@/lib/api/client";

export type SecureIndiaSource = {dataset_id: string; methodology: string; period_end: string; published_at: string; source_label: string; source_type: "SYNTHETIC"; version: string};
export type SecureIndiaRegion = {bucket: number; city: string; count: number; id: string; state: string; trend_percent: number; value: number; x: number; y: number; zone: string};
export type SecureIndiaLegendBin = {index: number; max: number | null; min: number};
export type SecureIndiaSummary = {
  available_cities: string[];
  available_states: string[];
  filters: {city: string; crime_type: string; period: "7d" | "30d" | "1y"; state: string; view: "count" | "per_lakh"};
  hot_crimes: Array<{count: number; id: string; resource_slug: string; share_percent: number}>;
  hot_zones: SecureIndiaRegion[];
  legend: SecureIndiaLegendBin[];
  map_regions: SecureIndiaRegion[];
  metrics: Array<{id: string; value: number}>;
  rankings: SecureIndiaRegion[];
  source: SecureIndiaSource;
};

export const secureIndiaApi = {
  summary: (query: URLSearchParams, options?: ApiRequestOptions) => apiClient.get<SecureIndiaSummary>("/secure-india/summary?" + query.toString(), options)
};
