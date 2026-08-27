import {getWarriorIdentity, getWarriorToken} from "./warrior-session";
import {getAccessToken, getMockIdentityProfile} from "./citizen-session";

// Enforces "only one login at a time" across the two independent session stores (citizen and
// warrior). Nothing before this stopped someone from ending up signed in as both at once - the
// warrior verify form and the citizen identity form each only ever looked at their own session
// key, so logging in on one side never checked whether the other side already had an active
// session. Call this before starting any new identity verification.
export type ActiveSession = {name: string; role: "citizen" | "warrior"};

export function getActiveSession(): ActiveSession | null {
  const warriorToken = getWarriorToken();
  const warriorIdentity = getWarriorIdentity();
  if (warriorToken && warriorIdentity) return {name: warriorIdentity.profile.full_name, role: "warrior"};

  const citizenToken = getAccessToken();
  const citizenProfile = getMockIdentityProfile();
  if (citizenToken && citizenProfile) return {name: citizenProfile.full_name, role: "citizen"};

  return null;
}
