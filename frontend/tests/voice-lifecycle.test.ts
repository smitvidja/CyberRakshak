import assert from "node:assert/strict";
import {beforeEach, test} from "node:test";

import {VoiceCaptureError, VoiceRecorder} from "../lib/cyber-saathi/voice-recorder";
import {VoiceSessionCoordinator} from "../lib/cyber-saathi/voice-session";

class FakeTrack {
  label = "Test microphone";
  readyState: MediaStreamTrackState = "live";
  getSettings() { return {channelCount: 1, sampleRate: 48000}; }
  stop() { this.readyState = "ended"; }
}

class FakeStream {
  readonly track = new FakeTrack();
  getAudioTracks() { return [this.track] as unknown as MediaStreamTrack[]; }
  getTracks() { return [this.track] as unknown as MediaStreamTrack[]; }
}

class FakeSource {
  connect() {}
  disconnect() {}
}

class FakePort {
  onmessage: ((event: MessageEvent<Float32Array>) => void) | null = null;
}

class FakeWorkletNode {
  static instances: FakeWorkletNode[] = [];
  readonly port = new FakePort();
  constructor() { FakeWorkletNode.instances.push(this); }
  connect() {}
  disconnect() {}
}

class FakeAudioContext {
  static failWorklet = false;
  readonly sampleRate = 48000;
  readonly destination = {};
  readonly audioWorklet = {addModule: async () => {
    if (FakeAudioContext.failWorklet) throw new DOMException("Worklet failed.", "NotSupportedError");
  }};
  async resume() {}
  createMediaStreamSource() { return new FakeSource() as unknown as MediaStreamAudioSourceNode; }
  async close() {}
}

class FakeMediaRecorder extends EventTarget {
  static isTypeSupported() { return true; }
  readonly mimeType = "audio/webm;codecs=opus";
  state: RecordingState = "inactive";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  start() { this.state = "recording"; }
  stop() {
    if (this.state === "inactive") return;
    this.state = "inactive";
    this.ondataavailable?.({data: new Blob(["mock-audio"], {type: this.mimeType})} as BlobEvent);
    this.dispatchEvent(new Event("stop"));
  }
}

let nextMediaRequest: () => Promise<MediaStream>;

function installBrowserMocks() {
  Object.defineProperty(globalThis, "window", {configurable: true, value: {btoa: (value: string) => Buffer.from(value, "binary").toString("base64")}});
  Object.defineProperty(globalThis, "navigator", {configurable: true, value: {mediaDevices: {getUserMedia: () => nextMediaRequest(), enumerateDevices: async () => [{deviceId: "test-mic", kind: "audioinput", label: "Test microphone"}]}}});
  Object.defineProperty(globalThis, "AudioContext", {configurable: true, value: FakeAudioContext});
  Object.defineProperty(globalThis, "AudioWorkletNode", {configurable: true, value: FakeWorkletNode});
  Object.defineProperty(globalThis, "MediaRecorder", {configurable: true, value: FakeMediaRecorder});
}

beforeEach(() => {
  FakeAudioContext.failWorklet = false;
  FakeWorkletNode.instances = [];
  nextMediaRequest = async () => new FakeStream() as unknown as MediaStream;
  installBrowserMocks();
});

test("session ownership rejects stale and competing callbacks", () => {
  const coordinator = new VoiceSessionCoordinator();
  const first = coordinator.begin();
  assert.ok(first);
  assert.equal(coordinator.begin(), null);
  assert.equal(coordinator.transition(first, "listening"), true);
  assert.equal(coordinator.transition(first, "finalizing"), true);
  assert.equal(coordinator.terminate(first), true);
  assert.equal(coordinator.transition(first, "fallback"), false);
  assert.equal(coordinator.release(first), true);
  const second = coordinator.begin();
  assert.ok(second);
  assert.notEqual(second.id, first.id);
  assert.equal(coordinator.transition(first, "listening"), false);
});

test("three consecutive recordings fully stop before the next begins", async () => {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const stream = new FakeStream();
    nextMediaRequest = async () => stream as unknown as MediaStream;
    const recorder = new VoiceRecorder();
    const audio: string[] = [];
    await recorder.start((chunk) => audio.push(chunk));
    const worklet = FakeWorkletNode.instances.at(-1);
    assert.ok(worklet?.port.onmessage);
    const samples = new Float32Array(4800).fill(0.05);
    for (let index = 0; index < 3; index += 1) worklet.port.onmessage({data: samples} as MessageEvent<Float32Array>);
    const firstStop = recorder.stop();
    const secondStop = recorder.stop();
    assert.equal(firstStop, secondStop);
    const recording = await firstStop;
    assert.equal(stream.track.readyState, "ended");
    assert.equal(recording.diagnostics.pcm_chunk_count, 3);
    assert.equal(recording.diagnostics.pcm_bytes, 9600);
    assert.equal(recording.diagnostics.speech_detected, true);
    assert.ok(recording.blob.size > 0);
    assert.equal(audio.length, 3);
  }
});

test("permission denial preserves the exact browser error", async () => {
  nextMediaRequest = async () => { throw new DOMException("Permission denied.", "NotAllowedError"); };
  const recorder = new VoiceRecorder();
  await assert.rejects(recorder.start(() => undefined), (error) => error instanceof VoiceCaptureError && error.stage === "permission" && error.browserName === "NotAllowedError");
  const recording = await recorder.stop();
  assert.equal(recording.diagnostics.browser_error_name, "NotAllowedError");
  assert.equal(recording.diagnostics.failure_stage, "permission");
});

test("worklet failure identifies its stage and releases the track", async () => {
  const stream = new FakeStream();
  nextMediaRequest = async () => stream as unknown as MediaStream;
  FakeAudioContext.failWorklet = true;
  const recorder = new VoiceRecorder();
  await assert.rejects(recorder.start(() => undefined), (error) => error instanceof VoiceCaptureError && error.stage === "audio-worklet" && error.browserName === "NotSupportedError");
  await recorder.stop();
  assert.equal(stream.track.readyState, "ended");
});
