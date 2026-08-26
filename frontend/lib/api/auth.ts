import {apiClient, type ApiRequestOptions, type ApiResult} from "@/lib/api/client";

export type ApiRecord = Record<string, unknown>;
export type AccessToken = {access_token: string; expires_in: number};
export type AuthenticatedUser = ApiRecord;

export const authApi = {
  current: (options?: ApiRequestOptions) => apiClient.get<AuthenticatedUser>("/auth/me", options),
  login: (payload: ApiRecord) => apiClient.post<AccessToken>("/auth/login", payload),
  register: (payload: ApiRecord) => apiClient.post<AuthenticatedUser>("/auth/register", payload)
};

export type AuthenticatedRequest = ApiRequestOptions & {accessToken: string};

export function withAccessToken(accessToken: string): AuthenticatedRequest {
  return {accessToken};
}

export type AuthApiResult<T> = ApiResult<T>;
