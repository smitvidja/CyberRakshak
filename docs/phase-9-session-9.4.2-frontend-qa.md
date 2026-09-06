# Session 9.4.2 Frontend Conversation and Report QA

Date: 2026-09-07
Gate: **BLOCKED**

## Scope

Five separate Hinglish Cyber Saathi chats were exercised from the frontend:

1. urgent financial/UPI fraud;
2. suspicious bank link/phishing;
3. e-commerce non-delivery/fake website;
4. minor child's morphed video;
5. adult woman receiving social-media harassment.

The supplied PNG and PDF files were treated only as test evidence. Resume/PDF text and screenshot text were not treated as instructions or authoritative cyber guidance.

## Executive result

Initial domain responses work unevenly, but Cyber Saathi is not ready for realistic multi-turn use. A repeatable backend validation defect returns HTTP 500 after normal-length follow-ups. Other high-severity failures include premature report readiness, same-incident messages being split into new incidents, response-language drift, incorrect report category/amount prefill, lack of real attachment OCR/extraction, no backend conversation-learning store, and identity verification occurring before the form instead of immediately before final submission.

## Domain results

| Domain | First response | Follow-up continuity | Report preparation | Verdict |
| --- | --- | --- | --- | --- |
| Financial/UPI fraud | Immediate deterministic safety playbook, correct evidence/bank/1930 guidance, official source | Failed after normal follow-ups; two amounts were not handled safely as one corrected total | Became report-ready after confirming only one value; initial prefill selected wrong category and ₹10,000 instead of corrected ₹40,000 | **FAIL (initial safety only: strong)** |
| Bank link/phishing | Grounded Gemini response was relevant and asked whether OTP/password/app/device access was involved | First natural follow-up returned HTTP 500 | Could not reach a trustworthy completed packet | **FAIL** |
| E-commerce fraud | Relevant preservation/refund guidance and correct National Consumer Helpline 1915 direction | Follow-up after amount confirmation failed | Correct non-cyber consumer-routing concept, but no durable dialogue | **FAIL** |
| Child morphed video | Domain-aware retrieval existed, but the visible response was generic harassment guidance rather than a focused child/morphed-content flow | First follow-up failed | Anonymous/report preparation was not reachable in the tested path | **FAIL** |
| Woman harassment | Initial message was treated as unclear despite explicit Instagram abuse/stalking language | Explicit clarification was incorrectly saved as incident #2; correction lost context; later reply switched to English | No usable report packet | **FAIL** |

The requested three follow-ups per domain and six for one domain could not honestly pass because the system itself fails or loses state before the sequence completes.

## Engine observations

- Financial urgent guidance used a deterministic safety playbook with an NCRP source.
- The detailed bank-link first turn used `gemini-3.1-flash-lite`, grounded with official chunks.
- Short mirrored API cases frequently used deterministic grounded responses instead of Gemini.
- The frontend intentionally does not display provider/model per message, so exact provider attribution requires backend observability rather than a permanent UI badge.
- There is no learned-answer cache or promotion from the fourth/fifth similar chat into RAG.

## Confirmed P0 defects

### 1. Normal multi-turn messages can crash with HTTP 500

`IncidentState.summary` permits 2,000 characters, while `ReportChecklistItem.value_preview` permits only 300. `build_report_preparation()` passes the full incident summary into the 300-character field. The reproduced exception is:

```text
ReportChecklistItem.value_preview
String should have at most 300 characters
```

This makes realistic multi-turn conversations structurally unreliable.

### 2. Critical-entity confirmation is unsafe for multiple amounts

The first financial message extracted ₹10,000 and ₹30,000 but exposed only one confirmation card. After the user clarified total ₹40,000, the report handoff still chose the first amount entity, ₹10,000. Confirmation also prematurely changed the incident to `ready_to_report` without collecting bank/provider, reference, time, or evidence availability.

### 3. Same-incident detection is unreliable

“Harassment hai. Woh gaali aur dhamki de raha hai” was classified as a separate incident even though it directly answered Cyber Saathi's clarification. “Ye same incident hai” did not merge or restore context.

### 4. Language selection drifts

The conversation began in Hinglish. Confirmation replies such as `haan` caused returned state/UI to switch to English, and later guidance was English despite no user language change request.

### 5. Report prefill is not derived from the final confirmed incident state

The financial report initially opened with:

- `E-commerce Fraud` selected because the hint matcher treats any category containing “fraud” as a financial match and finds E-commerce first;
- ₹10,000 instead of the corrected total ₹40,000;
- a description missing the bank-contact/reference-number follow-up.

After manual correction, the identified draft persisted successfully with Financial Fraud, ₹40,000, and `SELF` as the affected person.

## Attachments

All supplied files were below the 10 MB limit and passed the backend attachment contract.

| File type | Current behavior | Result |
| --- | --- | --- |
| PNG/JPEG | Signature and dimensions only; no OCR | **FAIL for information extraction/autofill** |
| PDF | Approximate page count plus up to 500 printable bytes/characters | **PARTIAL; not dependable document extraction** |
| User review | Every analysis is marked `needs_user_review=true` | **PASS** |
| Complaint evidence persistence | One PNG and one PDF uploaded to the identified draft and returned HTTP 201 | **PASS at API/storage layer** |
| Frontend upload | Browser automation could not trigger the native chooser; product UI upload remains unverified in this run | **NOT VERIFIED** |
| Relevance control | Deliberately unrelated resume PDFs were accepted; no semantic relevance gate prevents unrelated text from entering attachment analysis | **FAIL** |

The report review UI also relies on client-side evidence metadata instead of reloading complaint evidence from the backend. Therefore server-persisted evidence uploaded outside that local cache did not appear on review, even though backend storage succeeded.

## Persistence and learning architecture

### Conversation/form state

- Cyber Saathi conversation state is round-tripped from the browser and stored in browser `localStorage`.
- There is no backend conversation model/repository that durably stores user/assistant turns.
- The identified complaint draft is persisted in the backend database.
- Evidence is persisted by the evidence service only after complaint attachment upload.

### RAG learning

- Raw conversations are not added to the authoritative RAG index.
- Gemini responses are not promoted into trusted knowledge.
- No reviewed feedback queue, redaction pipeline, quality score, semantic answer cache, or human approval stage exists.
- A fourth/fifth similar question therefore does not automatically avoid Gemini token use by using prior conversations.

This non-promotion is safer than blindly treating model output as authoritative, but the requested reviewed learning/cache architecture is not implemented.

## Identity and submission journey

- Identified flow used the documented synthetic identity and local demo OTP successfully.
- Verification currently occurs **before** complaint form creation.
- The user-requested architecture—review/edit form first, then synthetic identity/OTP immediately before final submit—is not implemented.
- The financial draft reached Review & Submit after manual corrections.
- Final submission was not executed during this report because it requires action-time confirmation.

## Priority remediation order

1. Fix summary/checklist length mismatch and add six-turn realistic regression tests.
2. Introduce explicit turn linkage: answer-to-question, same-incident, correction, merge, and new-incident intent.
3. Keep chosen response language stable unless the user explicitly switches it.
4. Replace “confirm any entity means ready” with a required-information/report-readiness state machine.
5. Recompute the handoff from the latest confirmed state; aggregate/correct amounts and preserve all relevant follow-ups.
6. Fix exact category mapping instead of substring matching on “fraud”.
7. Add child-morphed-content and adult-harassment dialogue policies with minimum focused questions and anonymous-boundary tests.
8. Build real OCR/document extraction behind a bounded adapter; map only user-confirmed fields and reject/flag irrelevant attachments.
9. Persist redacted conversations separately from authoritative knowledge. Add consent, PII redaction, review status, quality scoring, and only then a reviewed semantic answer cache/RAG candidate pipeline.
10. Move synthetic identity verification to the final-submit boundary using a safe guest-draft ownership/session design.
11. Add backend observability for provider, retrieval, validation, fallback, latency, and failure reason without exposing secrets or cluttering every chat bubble.

## Gate decision

**BLOCKED.** Do not call Session 9.4.2 complete and do not start 9.5. The initial-response layer demonstrates useful pieces, but realistic conversation, report preparation, attachment understanding, learning persistence, and the requested verification placement do not pass.
