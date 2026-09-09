# Phase 9, Session 9.5: Sarvam Voice, Streaming, and Low-Latency Conversation

## Scope Matrix

| Requirement / state | Route / component | API / data boundary | Verification | Manual acceptance |
| --- | --- | --- | --- | --- |
| Provider capability | Cyber Saathi header and composer | `GET /api/v1/cyber-saathi/voice/capabilities`; server-side Sarvam key only | capability/config tests | Available and unavailable states are explicit |
| Ready / listening / partial transcript | `CyberSaathiConversation` voice controls | Session-owned browser microphone to backend WebSocket proxy; 16 kHz mono linear16 | lifecycle, WebSocket message, and PCM conversion tests | Quiet, normal, fast, interrupted, and long speech |
| Hindi / English / Hinglish STT | Same conversation surface | Sarvam Realtime STT (`saaras:v4` on the realtime endpoint), `hi-IN`-bounded Hinglish with `codemix`, and explicit English selection | language-mapping and transcript tests | Hindi, Hinglish, numbers, UPI IDs, URLs |
| REST STT fallback | Retry/fallback control | `POST /api/v1/cyber-saathi/voice/transcriptions`; supported short recordings only | mocked provider/API tests | WebSocket failure preserves a reviewable transcription or text path |
| Conversation continuity | Existing message pipeline | Final transcript enters the normal conversation API; no separate voice state machine | mixed text/voice regression | Voice starts/continues incidents and text can resume |
| Critical entity confirmation | Existing confirmation card | Existing understanding and conversation state remain authoritative | existing entity tests plus STT variants | Amounts, phones, UPI IDs, transaction IDs, URLs are never silently trusted |
| Streaming response audio | Assistant turn playback controls | `POST /api/v1/cyber-saathi/voice/speech` proxies Sarvam HTTP-streamed Bulbul audio | mocked stream tests | Speaking, paused, resumed, stopped, retry states |
| Failure / permissions | Inline voice status and diagnostic panel | Mic, worklet, recorder, network, and provider failures remain distinct; no provider key or microphone state enters storage | typed-stage and stale-event tests | Provider unavailable, network failure, permission denied |
| Latency | Inline diagnostic summary | Client timing plus safe backend/provider timing headers; no prompt/audio logging | timing schema tests | STT, conversation, retrieval/LLM, TTS first audio, and end-to-end are visible |
| Accessibility / responsive | Voice controls and live regions | Keyboard controls, labels, reduced motion, mobile layout | lint/build/browser checks | Desktop/mobile, keyboard, screen-reader live status |

## Verified Sarvam Contract (9 September 2026)

- Realtime STT uses `wss://api.sarvam.ai/speech-to-text-realtime/ws` with mono `linear16` audio at 8 or 16 kHz and emits `transcript.partial` and `transcript.final` events. The live service for this project accepts `saaras:v4` on that endpoint; it explicitly rejects the documentation-advertised `saaras:v4-realtime` name with `invalid_model`.
- `language_code=auto` supports adaptive detection; `mode=codemix` is intended for Hindi-English speech. Manual endpointing uses `speech_start`, `speech_end`, and `end` events.
- Short-file REST fallback uses `POST /speech-to-text`, supports WebM/WAV and other documented formats, and is limited to recordings under 30 seconds.
- Streaming TTS uses `POST /text-to-speech/stream`; Bulbul v3 supports code-mixed text, a 3,500-character maximum, and binary audio streaming.
- The Sarvam subscription key remains on the backend. Browser code connects only to CyberRakshak APIs.

## Delivered

- `SarvamVoiceAdapter` owns REST STT, realtime STT WebSocket relay, streamed TTS, tolerant language mapping, validation, timeouts, and controlled provider errors.
- The voice capability, short-recording fallback, response-audio, and realtime transcription routes keep the provider key server-side and return no-store responses.
- The Cyber Saathi composer now has text/voice modes, all required voice states, live/final transcription review, retry, pause/resume/stop, and a text fallback that never clears the incident.
- English, Hindi, and Hinglish use the same conversation API. Final speech transcripts remain editable and critical entities still pass through the existing confirmation boundary.
- The browser downsamples microphone audio to 16 kHz mono linear16 for realtime STT while retaining a WebM recording for REST fallback.
- Each recording now has a single session owner. Stale WebSocket/provider callbacks cannot overwrite a newer or terminal state, and a new attempt is unavailable until recorder, worklet, track, audio context, and socket cleanup completes.
- Microphone and AudioContext acquisition begins directly from the user's click. The provider connection starts only after local capture is ready, preventing a local microphone error from being mislabeled as provider downtime.
- The UI exposes the selected microphone, a live input meter, capture stage, sample rate, duration, chunk/byte counts, speech/clipping checks, and local-only recording playback. Device enumeration allows the next attempt to select the intended physical input instead of a virtual/loopback device.
- Supported browsers start TTS playback from streamed chunks through `MediaSource`; other browsers retain buffered playback.
- Latency is separated into microphone-to-STT, STT-to-response, retrieval, LLM response, TTS first audio, and end-to-end first useful response.

## Verification Results

| Gate | Result |
| --- | --- |
| Voice adapter/API tests | 8 passed |
| Browser voice lifecycle tests | 4 passed: stale callbacks, three consecutive recordings, permission denial, worklet failure/cleanup |
| Cyber Saathi regression | 159 passed |
| Full backend suite | 275 passed; one upstream TestClient deprecation warning |
| Frontend ESLint | Passed |
| TypeScript | Passed |
| Next.js production build | Passed; 56/56 pages generated |
| Live Sarvam TTS | 11,493-byte MP3; provider first audio 1,475.189 ms |
| Live Hinglish TTS to REST STT | `मेरे UPI से ₹10,000 कट गए।`; `hi-IN`; confidence 0.896; STT 431.82 ms |
| Live realtime STT | WebSocket `session.begin` followed by `transcript.final` for the same synthetic phrase |
| Browser desktop/mobile | English/Hindi, text continuity, voice-ready state, critical confirmation, no console errors, no 390 px horizontal overflow |
| Local physical-test startup | Corrected frontend API target from `localhost:8000` to `127.0.0.1:8000`; conversation startup completes and Start listening is enabled |
| Microphone fallback | Immediate processing feedback followed by a bounded Retry state when microphone capture remains unavailable |
| Microphone/provider isolation | Embedded-browser `TimeoutError` reports `Microphone needs attention`; backend receives no Sarvam WebSocket when local capture is not ready |
| Input-device discovery | Laptop microphone array, Bluetooth headset, Iriun Webcam, Virtual Audio Cable, and Sharing-Media inputs surfaced for explicit selection |

The browser acceptance fixture used a new synthetic incident: `Mere UPI se ₹10,000 kat gaye, UPI ID testuser@upi thi.` Both values appeared in the required confirmation card before they could enter the report workflow. The same incident remained present after switching from English to Hindi and from text to voice mode.

## Manual Test Matrix

| Scenario | Current evidence | Status |
| --- | --- | --- |
| Quiet room / normal speech | Live synthetic Hinglish REST and realtime provider round trips | Provider path passed; physical microphone run pending |
| Hinglish | `hi-IN` plus `codemix`; live synthetic transcript preserved Hindi script, UPI, and amount | Provider path passed; corrected physical input run pending |
| Numbers / UPI IDs / URLs / transaction IDs / phones | Existing entity regression plus browser confirmation card | Passed |
| Fast / emotional / distressed / long / interrupted speech | 30-second cap, manual endpoint events, retry/fallback logic, and failure tests | Physical speech-quality run pending |
| Network/provider failure | Controlled API/WebSocket errors; text and incident state remain available | Passed in automated tests |
| Microphone permission denied | `NotAllowedError` maps to a microphone-only retry and leaves text enabled; exact stage remains visible | Passed with browser mocks; physical browser denial pending |
| Response audio | Live streamed provider response; streaming/browser fallback implementation | Provider passed; audible device playback pending |

## Known Provider And Environment Limits

- Sarvam short-file REST STT accepts recordings under 30 seconds; longer interaction should stay on realtime STT or be segmented deliberately.
- Code-mix mode improves Hindi-English handling but does not make amounts, identifiers, names, or URLs trustworthy. CyberRakshak always requires confirmation for critical extracted values.
- A short realtime phrase may emit only a final transcript even though the contract supports partial events.
- TTS language selection is explicit (`en-IN` or `hi-IN`); Hinglish uses the Hindi voice path with code-mixed input text.
- Physical-room, emotional-speech, microphone-denial, and audible-speaker checks require an authorized device run. Automated browser testing did not grant microphone access or transmit ambient audio.

## Physical-Test Readiness Fix

The first authorized device attempt exposed two local-browser issues. The frontend bundle targeted `localhost:8000` while the local backend listened on `127.0.0.1:8000`, leaving conversation startup pending and disabling voice controls. Local frontend configuration and its example now use the proven `127.0.0.1` backend URL. The composer also reports conversation processing instead of incorrectly claiming Voice ready while startup is busy.

Some browser environments leave `getUserMedia` pending without accepting or denying permission. Microphone startup is now bounded to 15 seconds and returns a reviewable Retry state without clearing text or incident state.

The first physical speech attempt reached realtime STT but reduced both a Hindi/Hinglish harassment sentence and an English harassment sentence to `Hello`. The recorder was emitting individual AudioWorklet frames rather than Sarvam's documented approximately 100 ms / 3,200-byte linear16 chunks. The recorder now batches exactly 100 ms before forwarding, starts the manual speech turn before the first chunk, uses the accuracy-oriented balanced stream, and sends suspicious one-word results from multi-second recordings through the REST STT fallback before presenting them.

The next physical attempt exposed the deeper local orchestration defect: provider and microphone callbacks could overwrite the same status, while the UI could enable a new attempt before the previous capture resources finished closing. The voice hook now uses one monotonic session token, terminal-state protection, idempotent fallback, and awaited cleanup. Capture starts before the provider socket, so a microphone failure cannot contact or blame Sarvam. The machine also has multiple physical and virtual inputs; the product now exposes a microphone selector and local playback so the captured source can be proven before STT quality is judged.

The 0.5-second Retry failure was a separate contract mismatch rather than a microphone or recognition-quality fault. A direct WebSocket handshake received Sarvam's fatal `invalid_model` event approximately 70 ms after `speech_start`: the endpoint accepted `saaras:v3-realtime` and `saaras:v4`, but not the configured `saaras:v4-realtime`. The adapter now uses the live-accepted `saaras:v4` identifier. Provider failures occurring before usable speech is captured also retain their provider/network error instead of being overwritten by `NO_SPEECH_DETECTED`.

## Gate Status

Implementation, automated lifecycle regression, live provider contract, production build, and desktop/mobile browser gates pass. Session 9.5 remains open only for the authorized repeated physical microphone/speaker matrix above. Session 9.6 has not started.

## Checkpoint

Current implementation state: session-owned voice lifecycle, microphone selection/diagnostics, provider isolation, local playback, and fallback behavior implemented; physical-device acceptance pending.

Last confirmed passing check: 4 browser lifecycle tests, TypeScript, focused ESLint, 56-page production build, explicit microphone-device discovery, and 375 px browser acceptance with no overflow.

Exact blocker and evidence: the embedded browser cannot supply ambient microphone audio; the user's physical browser must confirm the selected microphone array, local playback, repeated Hindi/English transcripts, and audible TTS.

Single next action: select the laptop microphone array (or the intentionally used Bluetooth headset), run three consecutive local-playback/STT attempts, then send one transcript and confirm audible TTS.

Files currently changed: Session 9.5 backend adapter/routes/config/tests/docs and frontend voice hook/recorder/UI/types/i18n/API client.
