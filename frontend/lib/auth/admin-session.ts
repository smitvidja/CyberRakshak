const adminTokenKey = "cyberrakshak.admin-token";
const adminEmailKey = "cyberrakshak.admin-email";

// Deliberately separate from the citizen and warrior stores. An administrator
// reviewing knowledge gaps is not a citizen session, and mixing them would let
// getActiveSession report an admin as a signed-in citizen.
export function setAdminSession(accessToken: string, email: string) {
  localStorage.setItem(adminTokenKey, accessToken);
  localStorage.setItem(adminEmailKey, email);
}

export function getAdminToken() {
  return localStorage.getItem(adminTokenKey);
}

export function getAdminEmail() {
  return localStorage.getItem(adminEmailKey);
}

export function clearAdminSession() {
  localStorage.removeItem(adminTokenKey);
  localStorage.removeItem(adminEmailKey);
}
