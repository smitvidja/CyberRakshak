const TARGET_SAMPLE_RATE = 16000;
const MICROPHONE_PERMISSION_TIMEOUT_MS = 15000;
const STREAM_CHUNK_DURATION_MS = 100;
const DIAGNOSTIC_UPDATE_INTERVAL_MS = 250;
const SPEECH_RMS_THRESHOLD = 0.008;

export type VoiceCaptureStage =
  | "idle"
  | "audio-context"
  | "permission"
  | "media-stream"
  | "media-recorder"
  | "audio-worklet"
  | "capturing"
  | "stopping"
  | "stopped";

export type VoiceCaptureDiagnostics = {
  stage: VoiceCaptureStage;
  failure_stage: VoiceCaptureStage | null;
  browser_error_name: string | null;
  device_label: string;
  sample_rate: number | null;
  channel_count: number | null;
  track_state: MediaStreamTrackState | "unavailable";
  duration_ms: number;
  pcm_chunk_count: number;
  pcm_bytes: number;
  recording_bytes: number;
  rms_level: number;
  peak_level: number;
  clipping: boolean;
  speech_detected: boolean;
  mime_type: string;
};

export type VoiceRecording = {blob: Blob; diagnostics: VoiceCaptureDiagnostics};
export type VoiceInputDevice = {deviceId: string; label: string};

export class VoiceCaptureError extends Error {
  readonly browserName: string | null;
  readonly stage: VoiceCaptureStage;

  constructor(stage: VoiceCaptureStage, cause: unknown) {
    const browserName = cause instanceof DOMException || cause instanceof Error ? cause.name : null;
    super(`Voice capture failed during ${stage}.`);
    this.name = "VoiceCaptureError";
    this.browserName = browserName;
    this.stage = stage;
  }
}

export function resampleToLinear16(input: Float32Array, inputSampleRate: number) {
  const ratio = inputSampleRate / TARGET_SAMPLE_RATE;
  const outputLength = Math.max(1, Math.floor(input.length / ratio));
  const output = new Int16Array(outputLength);
  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(input.length, Math.floor((index + 1) * ratio));
    let sum = 0;
    for (let cursor = start; cursor < end; cursor += 1) sum += input[cursor];
    const sample = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output;
}

export function linear16ToBase64(samples: Int16Array) {
  const bytes = new Uint8Array(samples.buffer, samples.byteOffset, samples.byteLength);
  let binary = "";
  for (let index = 0; index < bytes.length; index += 1) binary += String.fromCharCode(bytes[index]);
  return window.btoa(binary);
}

export class VoiceRecorder {
  private audioContext: AudioContext | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: AudioWorkletNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private chunks: Blob[] = [];
  private stage: VoiceCaptureStage = "idle";
  private failureStage: VoiceCaptureStage | null = null;
  private browserErrorName: string | null = null;
  private startedAt = 0;
  private stoppedAt = 0;
  private pcmChunkCount = 0;
  private pcmBytes = 0;
  private pcmSampleCount = 0;
  private pcmSumSquares = 0;
  private peakLevel = 0;
  private clippedSamples = 0;
  private speechChunks = 0;
  private lastDiagnosticUpdate = 0;
  private stopPromise: Promise<VoiceRecording> | null = null;

  constructor(private readonly deviceId?: string) {}

  static async listAudioInputs(): Promise<VoiceInputDevice[]> {
    if (!navigator.mediaDevices?.enumerateDevices) return [];
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((device) => device.kind === "audioinput")
      .map((device, index) => ({deviceId: device.deviceId, label: device.label || `Microphone ${index + 1}`}));
  }

  async start(onAudio: (base64Audio: string) => void, onDiagnostics?: (diagnostics: VoiceCaptureDiagnostics) => void) {
    if (this.stage !== "idle" && this.stage !== "stopped") {
      throw new VoiceCaptureError(this.stage, new Error("CAPTURE_ALREADY_STARTED"));
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new VoiceCaptureError("permission", new Error("MEDIA_DEVICES_UNAVAILABLE"));
    }

    this.resetMetrics();
    this.startedAt = performance.now();
    let permissionTimer: ReturnType<typeof setTimeout> | null = null;
    let requestExpired = false;

    try {
      this.stage = "audio-context";
      this.audioContext = new AudioContext({latencyHint: "interactive"});

      // Initiate both operations before the first await so stricter browsers
      // retain the original button-click activation.
      const resumeRequest = this.audioContext.resume();
      this.stage = "permission";
      const mediaRequest = navigator.mediaDevices.getUserMedia({
        audio: {
          autoGainControl: true,
          channelCount: 1,
          deviceId: this.deviceId ? {exact: this.deviceId} : undefined,
          echoCancellation: true,
          noiseSuppression: true
        },
        video: false
      });
      void mediaRequest.then((stream) => {
        if (requestExpired) stream.getTracks().forEach((track) => track.stop());
      }).catch(() => undefined);

      await resumeRequest;
      this.mediaStream = await Promise.race([
        mediaRequest,
        new Promise<never>((_, reject) => {
          permissionTimer = setTimeout(() => {
            requestExpired = true;
            reject(new DOMException("Microphone permission timed out.", "TimeoutError"));
          }, MICROPHONE_PERMISSION_TIMEOUT_MS);
        })
      ]);
      if (permissionTimer) clearTimeout(permissionTimer);

      this.stage = "media-stream";
      const track = this.mediaStream.getAudioTracks()[0];
      if (!track || track.readyState !== "live") {
        throw new DOMException("No live microphone track was returned.", "NotReadableError");
      }

      this.stage = "media-recorder";
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      this.mediaRecorder = new MediaRecorder(this.mediaStream, {mimeType});
      this.chunks = [];
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size) this.chunks.push(event.data);
      };
      this.mediaRecorder.start(250);

      this.stage = "audio-worklet";
      await this.audioContext.audioWorklet.addModule("/audio/cyber-saathi-pcm-worklet.js");
      this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.processor = new AudioWorkletNode(this.audioContext, "cyber-saathi-pcm");
      const inputFramesPerChunk = Math.max(1, Math.round(this.audioContext.sampleRate * STREAM_CHUNK_DURATION_MS / 1000));
      const pendingFrames: Float32Array[] = [];
      let pendingFrameCount = 0;

      this.processor.port.onmessage = (event: MessageEvent<Float32Array>) => {
        if (this.stage !== "capturing") return;
        pendingFrames.push(event.data);
        pendingFrameCount += event.data.length;
        while (pendingFrameCount >= inputFramesPerChunk) {
          const audioChunk = new Float32Array(inputFramesPerChunk);
          let written = 0;
          while (written < inputFramesPerChunk) {
            const next = pendingFrames[0];
            const framesToCopy = Math.min(next.length, inputFramesPerChunk - written);
            audioChunk.set(next.subarray(0, framesToCopy), written);
            written += framesToCopy;
            pendingFrameCount -= framesToCopy;
            if (framesToCopy === next.length) pendingFrames.shift();
            else pendingFrames[0] = next.slice(framesToCopy);
          }
          this.observeChunk(audioChunk);
          const linear16 = resampleToLinear16(audioChunk, this.audioContext?.sampleRate ?? TARGET_SAMPLE_RATE);
          this.pcmChunkCount += 1;
          this.pcmBytes += linear16.byteLength;
          onAudio(linear16ToBase64(linear16));
          const now = performance.now();
          if (onDiagnostics && now - this.lastDiagnosticUpdate >= DIAGNOSTIC_UPDATE_INTERVAL_MS) {
            this.lastDiagnosticUpdate = now;
            onDiagnostics(this.diagnostics());
          }
        }
      };

      this.source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      this.stage = "capturing";
      onDiagnostics?.(this.diagnostics());
    } catch (error) {
      if (permissionTimer) clearTimeout(permissionTimer);
      this.failureStage = this.stage;
      this.browserErrorName = error instanceof DOMException || error instanceof Error ? error.name : null;
      throw error instanceof VoiceCaptureError ? error : new VoiceCaptureError(this.stage, error);
    }
  }

  diagnostics(): VoiceCaptureDiagnostics {
    const track = this.mediaStream?.getAudioTracks()[0];
    const settings = track?.getSettings();
    const durationMs = Math.max(0, Math.round((this.stoppedAt || performance.now()) - this.startedAt));
    const rmsLevel = this.pcmSampleCount ? Math.sqrt(this.pcmSumSquares / this.pcmSampleCount) : 0;
    return {
      stage: this.stage,
      failure_stage: this.failureStage,
      browser_error_name: this.browserErrorName,
      device_label: track?.label || "Default microphone",
      sample_rate: this.audioContext?.sampleRate ?? settings?.sampleRate ?? null,
      channel_count: settings?.channelCount ?? null,
      track_state: track?.readyState ?? "unavailable",
      duration_ms: durationMs,
      pcm_chunk_count: this.pcmChunkCount,
      pcm_bytes: this.pcmBytes,
      recording_bytes: this.chunks.reduce((total, chunk) => total + chunk.size, 0),
      rms_level: Number(rmsLevel.toFixed(5)),
      peak_level: Number(this.peakLevel.toFixed(5)),
      clipping: this.pcmSampleCount > 0 && this.clippedSamples / this.pcmSampleCount > 0.03,
      speech_detected: this.speechChunks * STREAM_CHUNK_DURATION_MS >= 300,
      mime_type: this.mediaRecorder?.mimeType || "audio/webm"
    };
  }

  stop() {
    if (this.stopPromise) return this.stopPromise;
    this.stopPromise = this.stopInternal();
    return this.stopPromise;
  }

  private async stopInternal(): Promise<VoiceRecording> {
    this.stage = "stopping";
    const recorder = this.mediaRecorder;
    await new Promise<void>((resolve) => {
      if (!recorder || recorder.state === "inactive") return resolve();
      recorder.addEventListener("stop", () => resolve(), {once: true});
      recorder.stop();
    });
    this.processor?.disconnect();
    if (this.processor) this.processor.port.onmessage = null;
    this.processor = null;
    this.source?.disconnect();
    this.source = null;
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    this.stoppedAt = performance.now();
    await this.audioContext?.close().catch(() => undefined);
    const mimeType = recorder?.mimeType || "audio/webm";
    const blob = new Blob(this.chunks, {type: mimeType});
    this.mediaRecorder = null;
    this.stage = "stopped";
    const diagnostics = {...this.diagnostics(), recording_bytes: blob.size, mime_type: mimeType};
    this.mediaStream = null;
    this.audioContext = null;
    return {blob, diagnostics};
  }

  private observeChunk(chunk: Float32Array) {
    let sumSquares = 0;
    let peak = 0;
    let clipped = 0;
    for (const sample of chunk) {
      const magnitude = Math.abs(sample);
      sumSquares += sample * sample;
      peak = Math.max(peak, magnitude);
      if (magnitude >= 0.98) clipped += 1;
    }
    const chunkRms = Math.sqrt(sumSquares / Math.max(1, chunk.length));
    if (chunkRms >= SPEECH_RMS_THRESHOLD) this.speechChunks += 1;
    this.pcmSampleCount += chunk.length;
    this.pcmSumSquares += sumSquares;
    this.peakLevel = Math.max(this.peakLevel, peak);
    this.clippedSamples += clipped;
  }

  private resetMetrics() {
    this.stopPromise = null;
    this.browserErrorName = null;
    this.failureStage = null;
    this.stoppedAt = 0;
    this.pcmChunkCount = 0;
    this.pcmBytes = 0;
    this.pcmSampleCount = 0;
    this.pcmSumSquares = 0;
    this.peakLevel = 0;
    this.clippedSamples = 0;
    this.speechChunks = 0;
    this.lastDiagnosticUpdate = 0;
  }
}
