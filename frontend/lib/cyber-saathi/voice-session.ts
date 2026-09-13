export type VoiceSessionPhase =
  | "preparing"
  | "connecting"
  | "listening"
  | "stopping"
  | "fallback"
  | "finalizing"
  | "closing";

export type VoiceSessionToken = {
  readonly id: number;
  phase: VoiceSessionPhase;
  terminal: boolean;
};

/** Owns the identity of the one voice attempt allowed to update the UI. */
export class VoiceSessionCoordinator {
  private active: VoiceSessionToken | null = null;
  private nextId = 0;

  begin(): VoiceSessionToken | null {
    if (this.active) return null;
    const token: VoiceSessionToken = {id: ++this.nextId, phase: "preparing", terminal: false};
    this.active = token;
    return token;
  }

  owns(token: VoiceSessionToken) {
    return this.active === token && !token.terminal;
  }

  isCurrent(token: VoiceSessionToken) {
    return this.active === token;
  }

  transition(token: VoiceSessionToken, phase: VoiceSessionPhase) {
    if (!this.owns(token)) return false;
    token.phase = phase;
    return true;
  }

  terminate(token: VoiceSessionToken) {
    if (!this.owns(token)) return false;
    token.terminal = true;
    token.phase = "closing";
    return true;
  }

  release(token: VoiceSessionToken) {
    if (this.active !== token || !token.terminal) return false;
    this.active = null;
    return true;
  }

  get hasActiveSession() {
    return this.active !== null;
  }
}

/**
 * Sarvam's batch speech-to-text refuses a recording longer than this, so the
 * realtime socket is the only path that can transcribe one.
 */
export const REST_FALLBACK_MAX_DURATION_MS = 29_000;

/**
 * How long to wait for the realtime provider's final transcript before retrying
 * over the batch endpoint.
 *
 * This was a flat four seconds, which is why a sixty-second recording behaved
 * like a thirty-second one. Nothing caps the recording at thirty: the API allows
 * sixty, and the REST endpoint accepts about five minutes of audio. But after
 * four quiet seconds the session gave up on the realtime path and retried over
 * batch - which refuses a recording that long, so the retry could never succeed
 * and the citizen was left with whatever partial text had arrived.
 *
 * A longer capture takes longer to finalise, so it is given the time. A short
 * one keeps the quick retry, because there batch genuinely can rescue it.
 */
export function restFallbackDelayMs(capturedMs: number): number {
  return capturedMs > REST_FALLBACK_MAX_DURATION_MS ? 15_000 : 4_000;
}
