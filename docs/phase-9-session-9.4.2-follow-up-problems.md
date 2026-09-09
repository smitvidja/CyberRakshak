# Phase 9 Session 9.4.2 — Follow-up Problems

This document is an evidence log for issues found during manual testing after the main Session 9.4.2 rerun. Entries remain open until they are diagnosed, fixed, and verified in the real localhost frontend.

## Problem 1 — Completed bank-block action repeats the same follow-up

**Status:** FIXED AND VERIFIED
**Recorded:** 8 September 2026
**Resolved:** 8 September 2026
**Surface:** `http://localhost:3000/en/cyber-saathi`
**Conversation language:** Hinglish

### Citizen journey

1. The citizen reports multiple unauthorised transactions from a business account, a total loss of approximately ₹18 lakh, and says a bank complaint has already been made.
2. Cyber Saathi gives immediate financial-safety guidance and asks the citizen to confirm the extracted amount and date.
3. Citizen: `haan`
4. Cyber Saathi confirms the amount and asks whether the bank/UPI provider was contacted and outgoing transactions were blocked.
5. Citizen: `ha bol diya hai`
6. Cyber Saathi asks the citizen to get outgoing transactions blocked.
7. Citizen: `karva diya block`
8. **Actual result:** Cyber Saathi repeats the same instruction to block outgoing transactions instead of advancing.
9. The text `kardiya block age batao` is visible in the input in the final screenshot but had not yet been sent; it is not counted as a server response in this evidence.

### Expected result

After `karva diya block`, the system should recognise the bank-protection action as completed, store that action against the current incident, and advance to the next missing report detail—for example transaction/UTR/reference number, payment evidence, or the next report-preparation question. It must not repeat the bank-block question.

The initial statement that a bank complaint was already made should also be retained so the system does not ask the citizen to reconfirm an action that was clearly provided earlier unless a genuinely different bank-protection detail is still missing.

### Actual failure

- The pending financial follow-up does not advance after the natural Hinglish completion phrase `karva diya block`.
- The same deterministic bank-protection response is returned again.
- This recreates the previously reported follow-up loop even though the wording is different from the phrases covered by earlier tests.

### Confirmed cause and correction

1. Action-completion matching compared the raw short reply too literally with the pending question, so joined and causative Hinglish variants such as `kardiya` and `karva diya` did not resolve `bank_protection`.
2. The opening statement `bank mein complaint kar di` was not being applied to the incident's completed financial actions.
3. The progress route now normalises joined/typo variants and resolves them against the stored pending question instead of treating a short reply as an isolated new incident.
4. Already-stated bank contact is recorded on the opening turn. After amount confirmation, the workflow asks only for the remaining protection action; after that action is completed, it advances to transaction/UTR/reference or evidence.

### Verification result

1. Focused exact/variant regression checks pass, including `karva diya block`, `kardiya block`, `block ho gaya`, and `outgoing band karwa diya`.
2. In the real `localhost:3000` UI, `kardiya block age batao` produced: “Bank wala action record ho gaya hai” and advanced to transaction/UTR/reference or payment evidence.
3. The live response did not repeat the completed bank-block instruction.
4. The complete backend suite passes: **267 passed**, with one known third-party Starlette/httpx deprecation warning.

### Required verification when this problem is fixed

1. Reproduce the exact conversation above in the real localhost frontend.
2. Inspect the API response/state before and after `karva diya block`.
3. Verify the pending question changes and `bank_protection_requested` is stored once.
4. Verify the next response asks a new, relevant report-detail question.
5. Add regression variants such as `karva diya block`, `kardiya block`, `block ho gaya`, and `outgoing band karwa diya` without hard-coding one full conversation.
6. Confirm that an ambiguous answer such as only `haan` does not falsely claim the block is complete when the pending question is merely bank contact.

### Evidence

- [Initial report and safety guidance](./evidence/phase-9-session-9.4.2-follow-up-problems/problem-1-initial-guidance.png)
- [Amount confirmation and follow-up sequence](./evidence/phase-9-session-9.4.2-follow-up-problems/problem-1-followup-sequence.png)
- [Repeated bank-block response](./evidence/phase-9-session-9.4.2-follow-up-problems/problem-1-repeated-question.png)

## Problem 2 — Child/intimate-image threats receive wrong or empty safety guidance

**Status:** FIXED AND VERIFIED
**Recorded:** 8 September 2026
**Resolved:** 8 September 2026
**Surface:** `http://localhost:3000/en/cyber-saathi`
**Conversation language:** Hinglish

### Case A — 15-year-old child, private-image coercion and financial blackmail

**Citizen:** A 15-year-old cousin was convinced by an online friend to send private photos. The person is threatening to leak the photos and demanding money. The child is frightened and needs immediate guidance.

**Actual result:** Cyber Saathi returns the Financial Fraud playbook: contact the bank/payment provider, block outgoing transactions, do not share OTP/PIN/password, and preserve transaction evidence.

**Failure:** The money-demand phrase appears to dominate the more important child-safety, grooming, intimate-image abuse, coercion, and blackmail signals. The answer has effectively no child-specific safety support.

**Expected primary routing:** `Women and child online safety` or `Child safety`, with financial extortion retained only as a related domain when relevant.

**Expected response qualities:**

1. Prioritise the child's immediate physical and emotional safety and involve a trusted adult.
2. Tell the child not to pay, negotiate, retaliate, or send more images.
3. Preserve identifiers, messages, timestamps, demands, profile URLs, and safe screenshots without downloading, forwarding, or redistributing intimate content.
4. Ask one relevant follow-up about immediate danger, ongoing contact, the platform/profile, and whether a trusted adult is present.
5. Offer the appropriate protected report workflow instead of making bank actions the primary response.

### Case B — Former partner threatens to publish private images

**Citizen:** A former partner has retained private photos and threatens to upload them if the citizen stops communicating. The citizen is frightened and asks where to report.

**Actual result:** Cyber Saathi only says that it can prepare an incident description and open the reporting flow for review.

**Failure:** No immediate safety guidance, evidence-preservation instruction, non-engagement advice, platform/account question, or specialised follow-up is provided. The response functions as a handoff placeholder rather than victim support.

**Expected primary routing:** At minimum `Online harassment / abuse`; use `Women and child online safety` when the affected-person context supports it. Blackmail, cyberstalking, or impersonation can remain related domains rather than replacing the primary safety route.

### Architecture concern raised by these cases

The current response path may be treating deterministic playbooks as complete even when the selected domain has weak or missing knowledge coverage. The implemented coverage across all 15 routing outcomes must be audited rather than assuming that a green classification/unit test means the answer is useful.

The intended simple decision flow is:

1. Classify the first message and follow-ups into one primary route and any related routes from the 15-route taxonomy:
   - Financial / UPI / card fraud
   - Phishing / fake link
   - Account compromise
   - Impersonation / fake authority
   - Identity theft / document misuse
   - E-commerce fraud / non-delivery
   - Malware / APK / remote access
   - Online harassment / abuse
   - Cyberstalking
   - Women and child online safety
   - Child safety
   - Misinformation / deepfake
   - Cyber-terrorism / serious threat
   - Other, explicitly self-labelled
   - Unknown / vague
2. Check whether the verified RAG/playbook library has sufficient, domain-appropriate coverage for the classified case.
3. If coverage is sufficient, retrieve grounded guidance from RAG and use it to answer and select the next specialised question.
4. If coverage is missing or below a defined quality threshold, send the redacted incident context to the configured LLM (currently Gemini) under the product's safety and non-invention constraints, rather than returning an irrelevant playbook or empty handoff sentence.
5. Keep deterministic code responsible for classification safeguards, state, confirmations, report fields, consent, and handoff. The LLM may generate supportive wording and candidate follow-ups, but it must not invent facts, mark actions complete, or bypass report validation.

### Dataset-growth requirement and safety boundary

Completed conversations should help improve weak categories, but raw victim chats must not automatically become live RAG knowledge or model-training data. The safe improvement loop to evaluate is:

1. Store a conversation only when the citizen gave explicit storage/improvement consent.
2. Remove or tokenise unnecessary identity, contact, financial, location, attachment, and other sensitive details.
3. Attach the primary/related domain labels and outcome metadata separately from the official guidance library.
4. Quarantine the redacted example in a review dataset; do not retrieve it as authoritative advice.
5. Require safety/quality review before extracting a reusable scenario, follow-up pattern, or playbook addition.
6. Rebuild/version the RAG index only from approved material and preserve source/provenance metadata.
7. Re-run the 15-route quality matrix after each approved knowledge expansion.

This preserves the requested growth path—weak categories can expand from reviewed real-world patterns—without allowing one unverified victim conversation or an LLM answer to teach unsafe guidance to the next citizen.

### Confirmed cause and correction

1. Broad financial terms such as `paise maang raha hai` could outrank the safety-critical child, grooming, coercion, private-image, leak, and blackmail signals.
2. A message containing the word `report` could enter the direct report-preparation branch before the specialised domain safety response and question flow ran.
3. The reviewed knowledge library already contains child grooming, image blackmail, harassment, and Women/Child guidance. These two failures were primarily routing and precedence defects, not proof that this knowledge was absent.
4. Safety-sensitive classification now runs before broad financial matching: explicit under-18 image coercion/threat routes to `child_safety`; adult intimate-image threat routes to `women_child_online_safety`, with related domains retained.
5. Recognised specialised domains can no longer be bypassed by the generic direct-report branch. They first receive concrete safety actions and exactly one relevant question.
6. When retrieval genuinely returns no adequate source, the service now permits a guarded Gemini answer with no fake source attribution, while deterministic code continues to own state, confirmations, safety controls, and report readiness.

### Verification result

1. The exact 15-year-old case returns primary domain `child_safety`, grounded child-specific guidance, trusted-adult involvement, no-payment/non-compliance advice, safe evidence handling, and one immediate-danger question. It does not return bank guidance.
2. In the real `localhost:3000` UI, answering `nahi` to immediate danger advanced to platform/profile/username/phone/URL details; it did not repeat or jump to an empty handoff.
3. The exact former-partner case returns concrete numbered intimate-image safety actions and one immediate-danger question instead of the generic “prepare an incident description” response.
4. The Cyber Saathi/RAG/domain contract suite passes: **197 passed**, with one known third-party warning.
5. The complete backend suite passes: **267 passed**, with the same known third-party warning.

### Required verification when this problem is fixed

1. Reproduce both exact cases in the real localhost frontend.
2. Inspect classification, related domains, retrieval strategy/scores, grounding status, LLM provider/fallback metadata, pending question, and final rendered answer.
3. Confirm the child case never receives a bank-first playbook solely because money is demanded.
4. Confirm both cases receive concrete, numbered safety actions followed by exactly one specialised question.
5. Confirm the questions advance through report preparation without repeating or skipping the editable report.
6. Add paraphrases in English, Hindi, Hinglish, typo-heavy Hinglish, and relationship variants without hard-coding the two full conversations.
7. Record which response came from approved RAG content and which required the guarded Gemini fallback.

### Evidence

- [Child private-image blackmail incorrectly receives financial guidance](./evidence/phase-9-session-9.4.2-follow-up-problems/problem-2-child-blackmail-wrong-financial-guidance.png)
- [Former-partner intimate-image threat receives no useful safety guidance](./evidence/phase-9-session-9.4.2-follow-up-problems/problem-2-intimate-image-threat-no-safety-help.png)
