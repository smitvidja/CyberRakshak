# Session 9.4.2 Test 2 — Corrective Cyber Saathi QA

Executed: 7–8 September 2026
Original QA: [`phase-9-session-9.4.2-frontend-qa.md`](./phase-9-session-9.4.2-frontend-qa.md)
Test-gap audit: [`phase-9-session-9.4.2-corrective-audit.md`](./phase-9-session-9.4.2-corrective-audit.md)

## Final verdict

**PASS for the requested local Cyber Saathi → editable report → mock identity/OTP → submission → dashboard → tracking workflow.**

This verdict is based on current automated tests plus real Codex in-app browser runs against the local production build. It does not claim access to live banks, Aadhaar/UIDAI, police, government systems, SMS, or external complaint portals.

The old statements “five-domain frontend passed,” “33 passed,” and “164 passed” are **superseded**. Those were API/build results presented too broadly and did not prove the actual frontend journey.

## Final verification gates

| Gate | Final result | Evidence |
| --- | --- | --- |
| Cyber Saathi, RAG, domain, state, and LLM-boundary suite | **186 passed** | Six focused test modules; one third-party Starlette/httpx deprecation warning |
| Complete backend suite | **256 passed** | Entire `backend/tests` suite; same single third-party warning |
| Mock identity focused suite | **6 passed** | Includes stale documented OTP-hash repair regression |
| Frontend ESLint | **PASS** | `npm run lint`, exit 0 |
| TypeScript | **PASS** | `npx tsc --noEmit`, exit 0; also checked by production build |
| Next.js production build | **PASS** | Compilation and TypeScript passed; **56 static pages** generated |
| Alembic drift | **PASS** | `No new upgrade operations detected.` |
| Four focused browser conversations | **PASS** | Exact visible responses recorded below; zero console warnings/errors |
| Complete browser Journey 1 | **PASS** | Financial fraud; submitted, dashboard, and tracking verified |
| Complete browser Journey 2 clean rerun | **PASS** | Phishing/account compromise; submitted, dashboard, and tracking verified |
| Final clean Journey 2 API log | **PASS** | Every product request was 200/201; no 4xx/5xx, traceback, or backend error |

## What was repaired

1. Composite Indian amounts such as `2 lakh 30 hazar` now produce one value, `₹2,30,000`.
2. Genuine multiple amounts remain ambiguous until the citizen types one corrected total; repeated `haan` cannot create an identical loop.
3. Every assistant question stores a question key, expected answer type, incident ID, and attempts.
4. Natural answers such as `ha bol diya`, `bank ko bol diya`, `kar diya`, and typo `account froe karwa diya` answer the pending question instead of starting generic chat.
5. Confirmed amounts and completed bank actions are not asked again unless a clear correction is supplied.
6. All 13 specialized domains now have deterministic safety actions, one specialized question at a time, yes/no/uncertain handling, checklist progression, and explicit draft preparation.
7. `Other` and `Unknown` are separately classified safe clarification routes; neither invents a reportable domain or handoff.
8. Cross-domain branching preserves related context: phishing + password, malware + loss, and impersonation + loss are not flattened into canned single-domain answers.
9. RAG/source cards remain supporting material. They do not choose state, confirmed facts, next question, readiness, or routes, and source content stays collapsed in the UI.
10. The report packet is grouped as Already collected, Need confirmation, and Useful but optional, with Add detail, Upload evidence, and Prepare report draft actions.
11. Prepare report is explicit. Merely saying “report” or confirming a fact does not silently create a handoff.
12. The report handoff persists across refresh and opens the existing editable form.
13. Guest incident saves now merge with the existing draft; revisiting and pressing Continue no longer deletes suspect identifiers or affected-person fields.
14. A missing financial amount now displays `-`, not the false value `₹0.00`.
15. Relative Hinglish date/time is preserved: `kal 6 pm` becomes the local form value `2026-09-07T18:00`, not a UTC-derived `05:30`.
16. Review and editing occur before identity. Mock identity and mock OTP appear only after final Submit.
17. Existing synthetic identity rows repair stale OTP hashes so the documented local OTP remains valid.
18. Submitted complaints appear in My Reports and open the matching tracking timeline.

## Fifteen-route × thirteen-area contract

Legend: `A` = route-specific automated contract; `A+B` = automated plus real browser evidence; `G` = automated safe guard that intentionally blocks report progression; `—` = not applicable because the route must remain unclassified/non-reportable.

The matrix is a behavioral contract, not a claim that 195 separate browser scripts were executed. Shared persistence, identity, submission, and tracking code is tested once at its boundary and then proven through two different full browser domains.

| # | Route | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Financial / UPI / card fraud | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B |
| 2 | Phishing / fake link | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B | A+B |
| 3 | Account compromise | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 4 | Impersonation / fake authority | A+B | A+B | A+B | A | A | A | A | A+B | A+B | A | A | A | A |
| 5 | Identity theft / document misuse | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 6 | E-commerce fraud / non-delivery | A+B | A+B | A+B | A | A | A | A | A+B | A+B | A | A | A | A |
| 7 | Malware / APK / remote access | A+B | A+B | A+B | A | A | A | A | A+B | A+B | A | A | A | A |
| 8 | Online harassment / abuse | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 9 | Cyberstalking | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 10 | Women and child online safety | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 11 | Child safety | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 12 | Misinformation / deepfake | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 13 | Cyber-terrorism / serious threat | A | A | A | A | A | A | A | A | A | A | A | A | A |
| 14 | Other, explicitly self-labelled | A | A | G | A | A | A | A | A | G | — | — | A | G |
| 15 | Unknown / vague | A | A | G | A | A | A | A | A | G | — | — | A | G |

The thirteen numbered areas are:

1. classification and domain stability;
2. fact-appropriate first safety response;
3. specialized next question or safe clarification;
4. stored expected-answer type;
5. contextual short-answer interpretation;
6. entity extraction and correction;
7. no repeated accepted question;
8. English, Hindi, Hinglish, and typo/STT-style coverage;
9. relevant grounding without a source dump;
10. report checklist progression;
11. correct editable prefill;
12. persistence and resume behavior;
13. safe handoff, final identity boundary, submission, dashboard, and tracking.

## Required cross-domain results

| Scenario | Result |
| --- | --- |
| Fake Ayushman/government lure + OTP + money lost | Financial Fraud primary; lure evidence retained |
| Fake cyber police, no stated loss | Impersonation; no automatic financial/1930 route |
| Fake cyber police + money transfer | Financial Fraud primary; Impersonation retained as related context |
| Fake KYC link + password entered | Phishing primary; Account Compromise retained as related context |
| APK/remote access + money loss | Financial Fraud primary; Malware retained as related context |
| Paid shopping order not delivered | E-commerce Fraud; payment alone does not promote it to Financial Fraud |

## Exact focused browser transcripts

All source material appeared only behind the collapsed `OFFICIAL SOURCE` control.

### 1. Financial composite amount

**Citizen:** `Mujhe fake government call aaya. Unhone 2 lakh 30 hazar transfer karwa liye. Ab kya karu?`

**Cyber Saathi:**

1. Bank/payment provider ke official channel—app, website ya card-back number—se contact karke outgoing transactions block karwayein.
2. Aur paise na bhejein aur OTP/PIN/password share na karein.
3. Screenshots, transaction details, provider reference aur chat ko evidence ke taur par preserve karein. In details ko confirm karein: amount: ₹2,30,000.

**Citizen:** `haan`

**Cyber Saathi:** `Amount confirm ho gaya hai. Ab kya aapne bank ya UPI provider ke official channel se unauthorized payment report karke outgoing transactions block karne ko bola hai?`

**Citizen:** `haan, bank ko official number se call kar diya`

**Cyber Saathi:** `Bank se contact karna record ho gaya hai. Unse outgoing transactions block karne aur payment ko fraud ke taur par note karne ko boliye. Bank ne koi reference number diya ya account protection action liya?`

**Citizen:** `account froe karwa diya bank se`

**Cyber Saathi:** `Bank wala action record ho gaya hai. Ab jo transaction/UTR/reference number ya payment screenshot/statement available ho, add karein. Baaki details report form mein edit kar sakte hain—transaction reference ya payment proof hai?`

**Citizen:** `UTR FIN230000 kal 4:30 pm ka hai`

**Cyber Saathi:** `Good. Incident packet aur checklist neeche ready hai. Extracted details review karein, available PDF/image evidence add karein, phir editable form ke liye reporting mode choose karein.`

Result: one confirmed amount, no repeated amount question, no main-answer CERT dump, no repeated 1930 escalation, and packet ready.

### 2. Fake cyber police

**Citizen:** `Nakli cyber police banke case ka dar dikha rahe hain.`

**Cyber Saathi:**

1. Call/chat end karein; paise transfer ya OTP, PIN, password, documents share na karein.
2. Organisation ke official public number/website se claim independently verify karein.
3. Caller number, profile, messages, case claim aur payment request preserve karein.

`Phone number, account, profile, case number, message ya payment detail mein se kya preserve hai?`

Result: Impersonation, not Financial Fraud; asks for caller/profile/channel evidence.

### 3. APK / remote access

**Citizen:** `Maine loan APK install kiya aur remote access de diya.`

**Cyber Saathi:**

1. Affected device ko mobile data, Wi-Fi aur remote sessions se disconnect karein.
2. Dusre trusted device se important accounts secure karke affected provider ko officially contact karein.
3. Evidence remove karne se pehle app/APK name, permissions, messages aur unknown activity save karein.

`App ya remote access ke baad paise gaye, ya koi account access/change hua?`

Result: Malware route; the stated install/remote-access fact is remembered; financial promotion requires an actual loss statement.

### 4. E-commerce non-delivery

**Citizen:** `Maine online order payment kiya, delivery nahi hui aur seller reply nahi kar raha.`

**Cyber Saathi:**

1. Order page, payment receipt, seller messages aur promised delivery date save rakhein.
2. Marketplace/seller ko sirf official support ya refund process se contact karein.
3. Refund ya delivery release karne ke naam par extra fee na dein.

`Aapke paas order number, seller name ya listing URL kya hai?`

Result: E-commerce Fraud, not Financial Fraud; asks for order/seller/listing information.

## Complete browser Journey 1 — Financial fraud

Final complaint: **`CR-2026-7FD4A726F7`**

Verified route sequence:

1. `/en/cyber-saathi` — composite amount shown as `₹2,30,000`; five natural follow-ups reached the packet.
2. Explicit Prepare report draft — Review and edit report appeared and survived refresh.
3. `/en/report-crime/new/incident` — Financial Fraud, amount `230000`, narrative, UTR, and date/time prefilled.
4. Citizen edited the title to `Financial fraud - verified by citizen`.
5. `/en/report-crime/guest-draft/incident` — edit and amount survived reload.
6. People and Review completed; no identity input existed before final Submit.
7. `/en/report-crime/verify` — documented synthetic identity `99000000000003`, local OTP `111222`.
8. `/en/complaints/submitted/CR-2026-7FD4A726F7` — submission success.
9. `/en/complaints` — exact edited title, reference, and Submitted state shown.
10. `/en/complaints/track/CR-2026-7FD4A726F7` — matching status timeline shown.

Evidence:

- [`journey-1-chat-draft-after-refresh.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-1-chat-draft-after-refresh.png)
- [`journey-1-editable-prefill.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-1-editable-prefill.png)
- [`journey-1-post-submit-mock-otp.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-1-post-submit-mock-otp.png)
- [`journey-1-submitted.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-1-submitted.png)
- [`journey-1-dashboard.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-1-dashboard.png)
- [`journey-1-tracking.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-1-tracking.png)

## Complete browser Journey 2 — Phishing/account compromise

Final clean-rerun complaint: **`CR-2026-DCB9B5F544`**

Conversation inputs:

1. `Mujhe KYC update ka fake link aaya, maine click karke password enter kar diya. Ab login nahi ho raha.`
2. `nahi, sirf password enter kiya tha`
3. `nahi, koi paisa debit ya transfer nahi hua`
4. `nahi, koi app install ya remote access nahi diya`
5. `official website se password reset try kiya, abhi login nahi ho raha`
6. `sender KYC-ALERT tha, link https://kyc-update.example/final kal 6 pm aaya tha`

Verified route sequence:

1. `/en/cyber-saathi` — Phishing remained primary, Account Compromise stayed related, and the six answers advanced six distinct stored questions.
2. Explicit Prepare report draft — Review and edit report appeared and survived refresh.
3. `/en/report-crime/new/incident` — phishing narrative, URL, and date/time were prefilled; financial amount remained empty.
4. Citizen edited the title to `KYC phishing - clean rerun`.
5. `/en/report-crime/guest-draft/incident` — title survived save and reload.
6. `/en/report-crime/guest-draft/people` — `Person 1` opened automatically with `https://kyc-update.example/final` prefilled after the reload/Continue sequence.
7. `/en/report-crime/guest-draft/review` — title and URL persisted; amount displayed `-`; identity and OTP inputs were absent.
8. Final Submit opened `/en/report-crime/verify`.
9. Documented synthetic identity `99000000000004` issued the local OTP and accepted `222333`.
10. `/en/complaints/submitted/CR-2026-DCB9B5F544` — submission success.
11. `/en/complaints` — exact edited title, reference, and Submitted state shown.
12. `/en/complaints/track/CR-2026-DCB9B5F544` — matching Submitted timeline shown.

Evidence:

- [`journey-2-clean-people-prefill.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-2-clean-people-prefill.png)
- [`journey-2-clean-post-submit-mock-otp.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-2-clean-post-submit-mock-otp.png)
- [`journey-2-clean-submitted.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-2-clean-submitted.png)
- [`journey-2-clean-dashboard.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-2-clean-dashboard.png)
- [`journey-2-clean-tracking.png`](./evidence/phase-9-session-9.4.2-test-2_7sept/journey-2-clean-tracking.png)

## Failures found during real browser testing and affected reruns

| Failure found | Correction | Rerun result |
| --- | --- | --- |
| Guest draft lost the phishing URL after Save → reload → Continue | Merge updated incident fields into the existing guest draft instead of replacing its workflow data | URL visible in `Person 1`, Review, dashboard-backed submission |
| Null loss rendered as `₹0.00` | Treat null/undefined/blank as missing | Review displays `-` |
| Existing synthetic identity `…00004` retained an old OTP hash | Repair existing demo seed hashes against the documented local fixture | Focused API regression passed; clean browser rerun accepted `222333` |
| `Other` existed in the enum but was not emitted/tested separately | Added explicit Other markers and safe no-handoff regressions | Included in final 15-route matrix |
| `kal 6 pm` lost the time and rendered as `05:30` | Combine relative date + time into local ISO date-time and prefer it in handoff | Browser form displays `2026-09-07T18:00` |

The first Journey 2 attempt after the guest-draft repair encountered the stale OTP defect. A diagnostic completion with another valid synthetic citizen produced `CR-2026-6658D921C1`, but it is **not** counted as the clean final pass because that attempt contained a 422. After repairing and testing the seed behavior, Journey 2 was rerun from a clean origin and produced `CR-2026-DCB9B5F544` with only successful requests.

## Remaining limitations and intentionally untested boundaries

1. The complaint database currently exposes six coarse categories. `phishing_scam` maps to the existing `Identity Misuse` form category while the Cyber Saathi state, title, narrative, related-domain context, and URL retain the exact Phishing classification. Adding a separate database category requires a product taxonomy decision and migration.
2. Tesseract code is present for PNG/JPEG OCR, but the workstation does not have the `tesseract` executable installed. The API honestly returns `unavailable`; deployment still needs Tesseract plus a readable-image smoke test.
3. Source cards are verified as collapsed supporting evidence; the four focused browser cases did not manually open every external source link.
4. Real Aadhaar/UIDAI, SMS, banks, UPI providers, police, government portals, and external complaint submission are intentionally absent and were not tested.
5. Sarvam STT/TTS is not part of this completed repair. The typed English/Hindi/Hinglish and typo/STT-style understanding contract is ready for that later integration, but microphone speech recognition/synthesis requires its own session and tests.

## Follow-up correction — optional suspect and incident location (8 September 2026)

The report-preparation contract was extended and verified after the main rerun:

1. Cyber Saathi now asks once for optional suspect details at the reporting boundary when no suspect phone, account, profile, username, UPI ID, email, or URL is already known. English, Hindi, and Hinglish copy explicitly says that `not known` / `pata nahi` is acceptable and does not block the report.
2. A supplied suspect description is retained in the saved handoff. Recognised `name`/`naam` and `alias`/`username` values fill their matching editable fields; the original answer remains in the involvement field so information is not discarded.
3. Transaction/UTR/reference numbers remain transaction evidence and are no longer copied into suspect contact fields.
4. The incident form now labels City, District, and State individually as optional and explains that the citizen can leave them blank.
5. A city already stated in chat is reused when recognised; the verified browser case carried `Pune` and its state mapping `Maharashtra` into the editable incident form.

Verification after this correction:

- Cyber Saathi API/understanding/knowledge/LLM suite: **180 passed**, with only the existing third-party Starlette/httpx deprecation warning.
- Frontend lint: **PASS**.
- TypeScript: **PASS**.
- Next.js production build: **PASS**, 56 pages generated. The first sandboxed build attempt compiled but its TypeScript worker could not spawn (`EPERM`); the permitted direct rerun completed successfully.
- Real localhost browser: **PASS** through an e-commerce conversation with four specialised follow-ups → optional suspect question → packet → Prepare report draft → Review and edit report → incident form → people form. The rendered form showed `City (optional): Pune`, `State (optional): Maharashtra`, the optional-location explanation, `Name: Rakesh`, `Alias: mobiledeal`, and the original suspect answer in `How were they involved? (optional)`. Browser console warnings/errors: none.

No other failure from the approved corrective prompt remains open in the implemented local prototype scope.
