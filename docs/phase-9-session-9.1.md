# Phase 9 Session 9.1 - Foundation and Conversation Architecture

## Scope Matrix

| Requirement/state | Route/component | API/data boundary | Verification |
| --- | --- | --- | --- |
| Entry and empty state | `/[locale]/cyber-saathi`, `CyberSaathiConversation` | `POST /cyber-saathi/conversations` | Desktop/mobile browser |
| Multi-turn conversation | `CyberSaathiConversation` | Validated state round-trips with each message | API test and reload persistence |
| Loading and error | Conversation panel | Central API client result handling | Browser and component state |
| Hindi/Hinglish | Language selector and localized shell | Language retained in incident and turns | API tests and browser flow |
| Urgent financial safety | Safety message card | Deterministic pre-provider routing | API test and browser flow |
| Critical entity confirmation | Confirmation card | Entity confidence and confirmation IDs | API test and browser flow |
| Anonymous/identified boundary | Reporting-mode control | Server rejects unsupported anonymous handoff | API test and browser flow |
| Report/tracking handoff | Safe-next-step panel | Typed `WorkflowHandoff` and complaint prefill | API test and href verification |
| Voice foundation | Microphone control and fallback | Provider-neutral `VoiceAdapter` protocol | Browser fallback state |
| Provider abstraction | Backend protocols | `LLMGateway`, `VoiceAdapter`, `SafetyPlaybook` | Python syntax/import gate |

## Architecture Decisions

- The frontend uses the existing ProductShell, next-intl, central API client, and citizen reporting routes.
- Session 9.1 is infrastructure-stateless: the browser persists the serializable conversation state and sends it with each message. Durable server persistence is deferred until the later integration session rather than adding an undocumented database table.
- Deterministic safety routing runs before any future LLM provider. Recent financial-loss language immediately returns the approved evidence/bank-provider/credential safety playbook.
- LLM and voice providers are backend protocols. Session 9.1 does not wire a real provider, dataset, RAG index, or Sarvam API.
- Anonymous reporting follows the existing product rule: it is available only for Women and Child Safety incidents. Unsupported anonymous handoffs are disabled in the UI and rejected by the service.
- Critical values cannot unlock the report handoff until confirmed.

## API Contracts

```text
POST /api/v1/cyber-saathi/conversations
POST /api/v1/cyber-saathi/conversations/{conversation_id}/messages
```

Both endpoints use the repository success envelope. Message requests contain the user message, current validated state, and optional reporting mode. Responses contain the next state, mock-provider marker, and the first-useful-response latency budget (2,900 ms total target).

## State Machine

Supported incident states:

```text
unknown -> suspected/identified/urgent
unknown/suspected -> awaiting_user_input
urgent -> awaiting_confirmation -> ready_to_report
identified -> guidance_given -> ready_to_report
ready_to_report -> report_started -> report_completed
unknown -> tracking_requested
any completed path -> resolved
```

The mock foundation currently exercises `unknown`, `urgent`, `awaiting_confirmation`, `awaiting_user_input`, `ready_to_report`, and `tracking_requested`. Remaining states are represented in the contract for later sessions.

## Taxonomy

- Intents: report incident, seek guidance, check identifier, track report, Cyber Warrior, general awareness, unknown.
- Crime domains: financial fraud, identity theft, online harassment, phishing/scam, malware, misinformation, child safety, cyber terrorism, other, unknown.
- Urgency: low, medium, high, critical.
- Sentiment: neutral, concerned, distressed, fearful, angry.
- Languages: English, Hindi, Hinglish, mixed/uncertain.
- Critical entities: amount, phone, UPI ID, transaction ID, provider, date/time, URL, email, account ID, username.
- Confidence: numeric 0-1 with low (<0.5), medium (0.5-0.79), and high (>=0.8) semantics.

## Design Acceptance

- Reused the approved victim-report ProductShell composition, restrained navy/white operational palette, breadcrumb, support band, 8px cards, and dense form hierarchy.
- Added a prominent home quick action and primary navigation entry.
- Verified empty, loading implementation, recovered error state, long message, urgent safety, confirmation, voice fallback, report mode, handoff, persistence, English, Hindi, and Hinglish states.
- Verified 1280px desktop and 390px mobile layouts with no document or message overflow.
- Safe CyberRakshak prototype branding remains in place; no prohibited government marks or live-system claims were introduced.

## Files Changed

- Backend: Cyber Saathi schemas, service, provider interfaces, route, router registration, and focused tests.
- Frontend: route, conversation feature, typed API client/contracts, ProductShell/home entry points, and English/Hindi messages.
- Documentation: this Session 9.1 report.

## Verification

- Focused backend: 6 passed.
- Full backend: 75 passed.
- TypeScript: passed.
- Frontend lint: passed.
- Production build: passed; 56 static/dynamic pages generated, including English and Hindi Cyber Saathi routes.
- Browser: desktop/mobile, persistence, 3,060-character unbroken message, urgent Hinglish, Hindi amount confirmation, voice fallback, identified handoff, anonymous financial restriction, and zero fresh console errors passed.
- Existing warning: Starlette reports its installed `TestClient` HTTPX compatibility deprecation; no test failed.

## Known Limitations

- Responses use explicit mock rules; understanding datasets are Session 9.2.
- Conversation persistence is browser-local and bounded to 50 turns; durable authenticated persistence comes later.
- Microphone currently presents a safe text fallback; Sarvam STT/TTS and streaming are Session 9.5.
- Complaint prefill transport into every form field is deferred to Session 9.6; the typed handoff and existing route integration are present.
- No RAG or live LLM provider is connected in this session.

## Exact Handoff to Session 9.2

1. Implement the language-aware understanding engine behind the existing schemas.
2. Add dataset preparation with source/language/script metadata and train/evaluation separation.
3. Replace mock keyword extraction with evaluated intent, crime, urgency, sentiment, entity, ambiguity, and confidence outputs.
4. Preserve deterministic safety routing, critical-entity confirmation, response-language continuity, and anonymous/identified boundaries.
5. Do not change the provider, voice, or workflow contracts unless an evaluation-backed gap is documented.

Session 9.2 has not been started.
