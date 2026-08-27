// Evidence file bytes are served as a raw (non-JSON-envelope) response, so this bypasses the
// shared apiClient (which expects a {success, data} envelope) and fetches + opens the file
// directly. The blob is opened via an object URL rather than a bare authenticated link, since a
// plain <a href> can't carry an Authorization header.
export async function openEvidenceFile(evidenceId: string, accessToken: string): Promise<boolean> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) return false;
  try {
    const response = await fetch(baseUrl.replace(/\/$/, "") + "/api/v1/evidence/" + evidenceId + "/file", {
      headers: {Authorization: "Bearer " + accessToken}
    });
    if (!response.ok) return false;
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, "_blank");
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    return true;
  } catch {
    return false;
  }
}
