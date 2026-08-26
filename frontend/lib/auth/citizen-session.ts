const reportModeKey = "cyberrakshak.report-mode";
const accessTokenKey = "cyberrakshak.access-token";

export function setReportMode(mode: "anonymous" | "identified") {
  sessionStorage.setItem(reportModeKey, mode);
}

export function getReportMode() {
  const value = sessionStorage.getItem(reportModeKey);
  return value === "anonymous" || value === "identified" ? value : null;
}

export function setAccessToken(accessToken: string) {
  sessionStorage.setItem(accessTokenKey, accessToken);
}

export function getAccessToken() {
  return sessionStorage.getItem(accessTokenKey);
}
