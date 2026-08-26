import type {ApiError} from "@/lib/api/client";

export type FormErrorState = {
  fieldErrors: Record<string, string>;
  formErrorKey?: string;
};

export function errorMessageKey(error: ApiError) {
  switch (error.code) {
    case "UNAUTHORIZED":
      return "apiErrors.unauthorized";
    case "FORBIDDEN":
      return "apiErrors.forbidden";
    case "NOT_FOUND":
      return "apiErrors.notFound";
    case "VALIDATION_ERROR":
      return "apiErrors.validation";
    case "NETWORK_ERROR":
      return "apiErrors.network";
    case "SERVER_ERROR":
      return "apiErrors.server";
    default:
      return "apiErrors.unknown";
  }
}

export function toFormErrorState(error: ApiError): FormErrorState {
  const details = error.details ?? {};
  const fieldErrors = Object.fromEntries(
    Object.entries(details).filter(([, value]) => typeof value === "string")
  ) as Record<string, string>;

  return {
    fieldErrors,
    formErrorKey: Object.keys(fieldErrors).length > 0 ? undefined : errorMessageKey(error)
  };
}
