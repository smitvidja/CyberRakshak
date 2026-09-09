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
