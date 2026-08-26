import {apiClient, type ApiRequestOptions} from "@/lib/api/client";
import type {ApiRecord} from "@/lib/api/auth";

export const usersApi = {
  getMyProfile: (options: ApiRequestOptions) => apiClient.get<ApiRecord>("/users/me/profile", options),
  saveMyProfile: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.put<ApiRecord>("/users/me/profile", payload, options)
};
