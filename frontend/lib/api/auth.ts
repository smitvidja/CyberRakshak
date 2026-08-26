import {apiClient, type ApiRequestOptions, type ApiResult} from "@/lib/api/client";

export type ApiRecord = Record<string, unknown>;
export type AccessToken = {access_token: string; expires_in: number};
export type AuthenticatedUser = ApiRecord;
export type MockIdentityOtpIssued = {expires_at: string; masked_mobile: string};
export type MockIdentityProfile = {
  address: string;
  age: number;
  city: string;
  date_of_birth: string;
  full_name: string;
  gender: string;
  postal_code: string;
  registered_mobile: string;
  state: string;
};
export type MockIdentityVerification = AccessToken & {profile: MockIdentityProfile};

export const authApi = {
  current: (options?: ApiRequestOptions) => apiClient.get<AuthenticatedUser>("/auth/me", options),
  login: (payload: ApiRecord) => apiClient.post<AccessToken>("/auth/login", payload),
  register: (payload: ApiRecord) => apiClient.post<AuthenticatedUser>("/auth/register", payload),
  requestMockIdentityOtp: (payload: {demo_identity_id: string}) => apiClient.post<MockIdentityOtpIssued>("/auth/mock-identity/request-otp", payload),
  verifyMockIdentityOtp: (payload: {demo_identity_id: string; otp: string}) => apiClient.post<MockIdentityVerification>("/auth/mock-identity/verify-otp", payload)
};

export type AuthenticatedRequest = ApiRequestOptions & {accessToken: string};

export function withAccessToken(accessToken: string): AuthenticatedRequest {
  return {accessToken};
}

export type AuthApiResult<T> = ApiResult<T>;