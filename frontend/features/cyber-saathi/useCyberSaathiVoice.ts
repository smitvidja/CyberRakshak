"use client";

import {useCallback, useEffect, useRef, useState} from "react";

import {cyberSaathiApi} from "@/lib/api/cyber-saathi";
import {
  VoiceCaptureError,
  VoiceRecorder,
  type VoiceCaptureDiagnostics,
  type VoiceInputDevice,
  type VoiceRecording
} from "@/lib/cyber-saathi/voice-recorder";
import {
  VoiceSessionCoordinator,
  type VoiceSessionToken
} from "@/lib/cyber-saathi/voice-session";
import type {SaathiLanguage, VoiceCapabilities, VoiceLatency} from "@/types/cyber-saathi";

export type VoiceStatus = "ready" | "listening" | "processing" | "transcription" | "speaking" | "paused" | "retry" | "unavailable";

type ActiveVoiceSession = {
  token: VoiceSessionToken;
  recorder: VoiceRecorder;
  socket: WebSocket | null;
  bufferedAudio: string[];
  streaming: boolean;
  streamStartedAt: number | null;
  capturePromise: Promise<VoiceRecording> | null;
  recording: VoiceRecording | null;
  fallbackPromise: Promise<void> | null;
  failureHandled: boolean;
  connectionTimer: ReturnType<typeof setTimeout> | null;
  fallbackTimer: ReturnType<typeof setTimeout> | null;
  maxRecordingTimer: ReturnType<typeof setTimeout> | null;
  completionMode: "review" | "send";
  latestTranscript: string;
};

// Sarvam's batch STT endpoint accepts only short recordings. Longer captures
// stay on the realtime path; if that path fails, preserve any partial text for
// review instead of sending an unsupported batch request.
const REST_FALLBACK_MAX_DURATION_MS = 29_000;

const EMPTY_LATENCY: VoiceLatency = {
  microphone_to_stt_ms: null,
  stt_to_response_ms: null,
  retrieval_ms: null,
  llm_ms: null,
  tts_first_audio_ms: null,
  end_to_end_first_response_ms: null
};

function appendAudioChunk(sourceBuffer: SourceBuffer, chunk: Uint8Array<ArrayBuffer>) {
  return new Promise<void>((resolve, reject) => {
    const cleanup = () => {
      sourceBuffer.removeEventListener("updateend", handleUpdateEnd);
      sourceBuffer.removeEventListener("error", handleError);
    };
    const handleUpdateEnd = () => {
      cleanup();
      resolve();
    };
    const handleError = () => {
      cleanup();
      reject(new Error("VOICE_STREAM_APPEND_FAILED"));
    };
    sourceBuffer.addEventListener("updateend", handleUpdateEnd, {once: true});
    sourceBuffer.addEventListener("error", handleError, {once: true});
    sourceBuffer.appendBuffer(chunk);
  });
}

function captureErrorCode(error: unknown) {
  if (error instanceof VoiceCaptureError && ["NotAllowedError", "SecurityError"].includes(error.browserName ?? "")) {
    return "MICROPHONE_PERMISSION_DENIED";
  }
  return "MICROPHONE_UNAVAILABLE";
}

function invalidCaptureCode(recording: VoiceRecording) {
  if (!recording.blob.size || !recording.diagnostics.speech_detected) return "NO_SPEECH_DETECTED";
  if (recording.diagnostics.clipping) return "MICROPHONE_AUDIO_DISTORTED";
  return null;
}

export function useCyberSaathiVoice({
  conversationId,
  language,
  onTranscript
}: {
  conversationId?: string;
  language: SaathiLanguage;
  onTranscript: (transcript: string, sendImmediately: boolean) => void;
}) {
  const [capabilities, setCapabilities] = useState<VoiceCapabilities | null>(null);
  const [status, setStatus] = useState<VoiceStatus>("ready");
  const [partialTranscript, setPartialTranscript] = useState("");
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [latency, setLatency] = useState<VoiceLatency>(EMPTY_LATENCY);
  const [captureDiagnostics, setCaptureDiagnostics] = useState<VoiceCaptureDiagnostics | null>(null);
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null);
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null);
  const [inputDevices, setInputDevices] = useState<VoiceInputDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const coordinatorRef = useRef(new VoiceSessionCoordinator());
  const activeSessionRef = useRef<ActiveVoiceSession | null>(null);
  const recordingUrlRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const speechAbortRef = useRef<AbortController | null>(null);
  const statusRef = useRef<VoiceStatus>("ready");

  const updateStatus = useCallback((next: VoiceStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  useEffect(() => {
    void cyberSaathiApi.voiceCapabilities().then((result) => {
      if (result.ok) {
        setCapabilities(result.data);
        updateStatus(result.data.configured ? "ready" : "unavailable");
      } else {
        updateStatus("unavailable");
      }
    });
    void VoiceRecorder.listAudioInputs().then(setInputDevices).catch(() => undefined);
  }, [updateStatus]);

  const clearSessionTimers = useCallback((session: ActiveVoiceSession) => {
    if (session.connectionTimer) clearTimeout(session.connectionTimer);
    if (session.fallbackTimer) clearTimeout(session.fallbackTimer);
    if (session.maxRecordingTimer) clearTimeout(session.maxRecordingTimer);
    session.connectionTimer = null;
    session.fallbackTimer = null;
    session.maxRecordingTimer = null;
  }, []);

  const replaceRecordingUrl = useCallback((recording: VoiceRecording | null) => {
    if (recordingUrlRef.current) URL.revokeObjectURL(recordingUrlRef.current);
    const nextUrl = recording?.blob.size ? URL.createObjectURL(recording.blob) : null;
    recordingUrlRef.current = nextUrl;
    setRecordingUrl(nextUrl);
    if (recording) setCaptureDiagnostics(recording.diagnostics);
  }, []);

  const stopCapture = useCallback(async (session: ActiveVoiceSession) => {
    if (!session.capturePromise) {
      session.capturePromise = session.recorder.stop().then((recording) => {
        session.recording = recording;
        if (coordinatorRef.current.isCurrent(session.token)) replaceRecordingUrl(recording);
        return recording;
      });
    }
    return session.capturePromise;
  }, [replaceRecordingUrl]);

  const finalizeSession = useCallback(async (session: ActiveVoiceSession) => {
    if (!coordinatorRef.current.isCurrent(session.token)) return session.recording;
    coordinatorRef.current.terminate(session.token);
    clearSessionTimers(session);
    session.streaming = false;
    if (session.socket) {
      session.socket.onmessage = null;
      session.socket.onerror = null;
      session.socket.onclose = null;
      if (session.socket.readyState === WebSocket.CONNECTING || session.socket.readyState === WebSocket.OPEN) session.socket.close();
    }
    const recording = await stopCapture(session);
    if (activeSessionRef.current === session) activeSessionRef.current = null;
    coordinatorRef.current.release(session.token);
    return recording;
  }, [clearSessionTimers, stopCapture]);

  const runRestFallback = useCallback((session: ActiveVoiceSession, providerFailureCode?: string) => {
    if (session.fallbackPromise) return session.fallbackPromise;
    session.fallbackPromise = (async () => {
      if (!coordinatorRef.current.owns(session.token)) return;
      coordinatorRef.current.transition(session.token, "fallback");
      updateStatus("processing");
      clearSessionTimers(session);
      session.streaming = false;
      if (session.socket) {
        session.socket.onmessage = null;
        session.socket.onerror = null;
        session.socket.onclose = null;
        if (session.socket.readyState === WebSocket.CONNECTING || session.socket.readyState === WebSocket.OPEN) session.socket.close();
      }
      const recording = await stopCapture(session);
      const captureError = invalidCaptureCode(recording);
      if (captureError) {
        await finalizeSession(session);
        // A provider/socket failure can happen before the citizen has time to
        // speak. Preserve that root cause instead of blaming the microphone.
        setErrorCode(providerFailureCode ?? captureError);
        updateStatus("retry");
        return;
      }
      if (recording.diagnostics.duration_ms > REST_FALLBACK_MAX_DURATION_MS) {
        await finalizeSession(session);
        const transcript = session.latestTranscript.trim();
        if (transcript) {
          setPartialTranscript(transcript);
          onTranscript(transcript, false);
          setErrorCode(null);
          updateStatus("transcription");
        } else {
          setErrorCode(providerFailureCode ?? "RECORDING_TOO_LONG");
          updateStatus("retry");
        }
        return;
      }
      const result = await cyberSaathiApi.transcribeRecording(recording.blob, language);
      if (!coordinatorRef.current.owns(session.token)) return;
      await finalizeSession(session);
      if (result.ok) {
        const transcript = result.data.transcript.trim();
        setPartialTranscript(transcript);
        setDetectedLanguage(result.data.detected_language_code);
        onTranscript(transcript, session.completionMode === "send");
        setLatency((current) => ({...current, microphone_to_stt_ms: result.data.stt_latency_ms}));
        setErrorCode(null);
        updateStatus("transcription");
      } else {
        setErrorCode(result.error.code);
        updateStatus(result.error.code === "VOICE_PROVIDER_UNAVAILABLE" ? "unavailable" : "retry");
      }
    })();
    return session.fallbackPromise;
  }, [clearSessionTimers, finalizeSession, language, onTranscript, stopCapture, updateStatus]);

  const handleProviderFailure = useCallback(async (session: ActiveVoiceSession, code: string) => {
    if (!coordinatorRef.current.owns(session.token) || session.failureHandled) return;
    session.failureHandled = true;
    if (["listening", "stopping"].includes(session.token.phase)) {
      await runRestFallback(session, code);
      return;
    }
    await finalizeSession(session);
    setErrorCode(code);
    updateStatus(code === "VOICE_PROVIDER_UNAVAILABLE" ? "unavailable" : "retry");
  }, [finalizeSession, runRestFallback, updateStatus]);

  const finalizeTranscript = useCallback(async (session: ActiveVoiceSession, transcript: string) => {
    if (!coordinatorRef.current.owns(session.token) || ["fallback", "finalizing"].includes(session.token.phase)) return;
    coordinatorRef.current.transition(session.token, "finalizing");
    updateStatus("processing");
    const recording = await stopCapture(session);
    const captureError = invalidCaptureCode(recording);
    if (captureError) {
      await finalizeSession(session);
      setErrorCode(captureError);
      updateStatus("retry");
      return;
    }
    const elapsed = session.streamStartedAt ? performance.now() - session.streamStartedAt : 0;
    const wordCount = transcript.split(/\s+/u).filter(Boolean).length;
    if (elapsed >= 1500 && wordCount <= 1) {
      session.token.phase = "stopping";
      await runRestFallback(session);
      return;
    }
    await finalizeSession(session);
    setPartialTranscript(transcript);
    onTranscript(transcript, session.completionMode === "send");
    setLatency((current) => ({...current, microphone_to_stt_ms: Math.round(elapsed)}));
    setErrorCode(null);
    updateStatus("transcription");
  }, [finalizeSession, onTranscript, runRestFallback, stopCapture, updateStatus]);

  const stopListening = useCallback(async (completionMode: "review" | "send" = "review") => {
    const session = activeSessionRef.current;
    if (!session || !coordinatorRef.current.owns(session.token) || session.token.phase !== "listening") return;
    session.completionMode = completionMode;
    coordinatorRef.current.transition(session.token, "stopping");
    updateStatus("processing");
    if (session.maxRecordingTimer) clearTimeout(session.maxRecordingTimer);
    session.maxRecordingTimer = null;
    session.streaming = false;
    if (session.socket?.readyState === WebSocket.OPEN) session.socket.send(JSON.stringify({event: "speech_end"}));
    await stopCapture(session);
    session.fallbackTimer = setTimeout(() => void runRestFallback(session), 4000);
  }, [runRestFallback, stopCapture, updateStatus]);

  const finishAndSend = useCallback(() => stopListening("send"), [stopListening]);

  const startListening = useCallback(async () => {
    if (["listening", "processing"].includes(statusRef.current) || coordinatorRef.current.hasActiveSession) return;
    if (!conversationId || !capabilities?.configured) {
      setErrorCode("VOICE_PROVIDER_UNAVAILABLE");
      updateStatus("unavailable");
      return;
    }

    const token = coordinatorRef.current.begin();
    if (!token) return;
    const session: ActiveVoiceSession = {
      token,
      recorder: new VoiceRecorder(selectedDeviceId || undefined),
      socket: null,
      bufferedAudio: [],
      streaming: false,
      streamStartedAt: null,
      capturePromise: null,
      recording: null,
      fallbackPromise: null,
      failureHandled: false,
      connectionTimer: null,
      fallbackTimer: null,
      maxRecordingTimer: null,
      completionMode: "review",
      latestTranscript: ""
    };
    activeSessionRef.current = session;
    replaceRecordingUrl(null);
    setCaptureDiagnostics(null);
    setDetectedLanguage(null);
    setPartialTranscript("");
    setErrorCode(null);
    setLatency(EMPTY_LATENCY);
    updateStatus("processing");

    try {
      await session.recorder.start((audio) => {
        if (!coordinatorRef.current.owns(token)) return;
        if (session.streaming && session.socket?.readyState === WebSocket.OPEN) {
          session.socket.send(JSON.stringify({event: "audio_input", audio}));
        } else {
          session.bufferedAudio.push(audio);
          if (session.bufferedAudio.length > 50) session.bufferedAudio.shift();
        }
      }, (diagnostics) => {
        if (coordinatorRef.current.owns(token)) setCaptureDiagnostics(diagnostics);
      });
      void VoiceRecorder.listAudioInputs().then((devices) => {
        if (!coordinatorRef.current.isCurrent(token)) return;
        setInputDevices(devices);
        if (!selectedDeviceId && devices.length === 1) setSelectedDeviceId(devices[0].deviceId);
      }).catch(() => undefined);
    } catch (error) {
      const code = captureErrorCode(error);
      await finalizeSession(session);
      setErrorCode(code);
      updateStatus("retry");
      return;
    }

    if (!coordinatorRef.current.transition(token, "connecting")) {
      await stopCapture(session);
      return;
    }

    const socket = new WebSocket(cyberSaathiApi.voiceSocketUrl(conversationId, language));
    session.socket = socket;
    session.connectionTimer = setTimeout(
      () => void handleProviderFailure(session, "VOICE_NETWORK_ERROR"),
      8000
    );
    socket.onmessage = (event) => {
      if (!coordinatorRef.current.owns(token)) return;
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(String(event.data));
      } catch {
        return;
      }
      if (typeof payload.language === "string") setDetectedLanguage(payload.language);
      if (payload.event === "voice.ready" && token.phase === "connecting") {
        if (session.connectionTimer) clearTimeout(session.connectionTimer);
        session.connectionTimer = null;
        session.streamStartedAt = performance.now();
        session.streaming = true;
        socket.send(JSON.stringify({event: "speech_start"}));
        for (const audio of session.bufferedAudio) socket.send(JSON.stringify({event: "audio_input", audio}));
        session.bufferedAudio = [];
        coordinatorRef.current.transition(token, "listening");
        updateStatus("listening");
        session.maxRecordingTimer = setTimeout(
          () => void stopListening("review"),
          (capabilities.max_recording_seconds || 60) * 1000
        );
      } else if (payload.event === "transcript.partial" && typeof payload.text === "string") {
        session.latestTranscript = payload.text;
        setPartialTranscript(payload.text);
      } else if (payload.event === "transcript.final" && typeof payload.text === "string" && payload.text.trim()) {
        session.latestTranscript = payload.text.trim();
        void finalizeTranscript(session, payload.text.trim());
      } else if (payload.event === "voice.error" || payload.event === "error") {
        void handleProviderFailure(session, typeof payload.code === "string" ? payload.code : "VOICE_PROVIDER_UNAVAILABLE");
      }
    };
    socket.onerror = () => void handleProviderFailure(session, "VOICE_NETWORK_ERROR");
    socket.onclose = () => void handleProviderFailure(session, "VOICE_NETWORK_ERROR");
  }, [capabilities, conversationId, finalizeSession, finalizeTranscript, handleProviderFailure, language, replaceRecordingUrl, selectedDeviceId, stopCapture, stopListening, updateStatus]);

  const stopSpeech = useCallback(() => {
    speechAbortRef.current?.abort();
    speechAbortRef.current = null;
    const audio = audioRef.current;
    if (audio) {
      // Detach first. pause() fires its event on a queued task, not synchronously,
      // so onpause used to run *after* this function had already dropped the
      // element and set the status to "ready" - overwriting it with "paused" for a
      // clip that no longer exists and whose object URL had just been revoked. The
      // citizen was then shown a resume button with nothing behind it.
      audio.onplay = null;
      audio.onpause = null;
      audio.onended = null;
      audio.pause();
    }
    audioRef.current = null;
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    audioUrlRef.current = null;
    if (statusRef.current === "speaking" || statusRef.current === "paused") updateStatus("ready");
  }, [updateStatus]);

  const speak = useCallback(async (text: string, responseLanguage: SaathiLanguage) => {
    stopSpeech();
    const controller = new AbortController();
    speechAbortRef.current = controller;
    updateStatus("processing");
    const started = performance.now();
    try {
      const response = await cyberSaathiApi.synthesizeSpeech(text, responseLanguage, controller.signal);
      if (!response.ok || !response.body) throw new Error("VOICE_PROVIDER_UNAVAILABLE");
      const providerFirstAudio = Number(response.headers.get("x-tts-first-audio-ms"));
      const reader = response.body.getReader();
      const contentType = response.headers.get("content-type")?.split(";", 1)[0] ?? "audio/mpeg";
      let browserFirstChunk: number | null = null;

      const createAudio = (url: string) => {
        audioUrlRef.current = url;
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onplay = () => updateStatus("speaking");
        audio.onpause = () => { if (!audio.ended) updateStatus("paused"); };
        audio.onended = () => updateStatus("ready");
        return audio;
      };

      if (typeof MediaSource !== "undefined" && MediaSource.isTypeSupported(contentType)) {
        const mediaSource = new MediaSource();
        const audio = createAudio(URL.createObjectURL(mediaSource));
        await new Promise<void>((resolve, reject) => {
          mediaSource.addEventListener("sourceopen", () => resolve(), {once: true});
          mediaSource.addEventListener("error", () => reject(new Error("VOICE_STREAM_OPEN_FAILED")), {once: true});
        });
        const sourceBuffer = mediaSource.addSourceBuffer(contentType);
        let playbackRequested = false;
        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          if (!value?.length) continue;
          if (browserFirstChunk === null) browserFirstChunk = performance.now() - started;
          await appendAudioChunk(sourceBuffer, value);
          if (!playbackRequested) {
            playbackRequested = true;
            void audio.play().catch(() => {
              setErrorCode("VOICE_PLAYBACK_FAILED");
              updateStatus("paused");
            });
          }
        }
        if (mediaSource.readyState === "open") mediaSource.endOfStream();
      } else {
        const chunks: ArrayBuffer[] = [];
        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          if (browserFirstChunk === null) browserFirstChunk = performance.now() - started;
          if (value?.length) chunks.push(new Uint8Array(value).buffer);
        }
        const blob = new Blob(chunks, {type: contentType});
        const audio = createAudio(URL.createObjectURL(blob));
        await audio.play();
      }

      setLatency((current) => ({
        ...current,
        tts_first_audio_ms: Number.isFinite(providerFirstAudio) ? providerFirstAudio : browserFirstChunk === null ? null : Math.round(browserFirstChunk)
      }));
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setErrorCode("VOICE_PLAYBACK_FAILED");
      updateStatus(audioRef.current ? "paused" : "retry");
    }
  }, [stopSpeech, updateStatus]);

  const toggleSpeech = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) {
      // Nothing left to resume. Returning silently left the citizen pressing a
      // button that did nothing and gave no reason, so leave the paused state
      // instead of sitting in it.
      updateStatus(capabilities?.configured ? "ready" : "unavailable");
      return;
    }
    if (audio.paused) {
      // play() rejects on autoplay policy or a revoked source; swallowing that
      // left the UI claiming "paused" forever.
      void audio.play().catch(() => {
        setErrorCode("VOICE_PLAYBACK_FAILED");
        updateStatus(capabilities?.configured ? "ready" : "unavailable");
      });
    } else {
      audio.pause();
    }
  }, [capabilities, updateStatus]);

  const recordConversationLatency = useCallback((values: Partial<VoiceLatency>) => {
    setLatency((current) => ({...current, ...values}));
  }, []);

  const resetVoice = useCallback(() => {
    const session = activeSessionRef.current;
    updateStatus("processing");
    void (async () => {
      if (session) await finalizeSession(session);
      stopSpeech();
      replaceRecordingUrl(null);
      setCaptureDiagnostics(null);
      setDetectedLanguage(null);
      setPartialTranscript("");
      setErrorCode(null);
      setLatency(EMPTY_LATENCY);
      updateStatus(capabilities?.configured ? "ready" : "unavailable");
    })();
  }, [capabilities, finalizeSession, replaceRecordingUrl, stopSpeech, updateStatus]);

  useEffect(() => () => {
    const session = activeSessionRef.current;
    if (session && coordinatorRef.current.owns(session.token)) {
      coordinatorRef.current.terminate(session.token);
      clearSessionTimers(session);
      if (session.socket) {
        session.socket.onmessage = null;
        session.socket.onerror = null;
        session.socket.onclose = null;
        session.socket.close();
      }
      void session.recorder.stop();
    }
    speechAbortRef.current?.abort();
    audioRef.current?.pause();
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    if (recordingUrlRef.current) URL.revokeObjectURL(recordingUrlRef.current);
  }, [clearSessionTimers]);

  return {
    capabilities,
    captureDiagnostics,
    detectedLanguage,
    errorCode,
    finishAndSend,
    latency,
    inputDevices,
    partialTranscript,
    recordConversationLatency,
    recordingUrl,
    resetVoice,
    speak,
    selectedDeviceId,
    setSelectedDeviceId,
    startListening,
    status,
    stopListening,
    stopSpeech,
    toggleSpeech
  };
}
