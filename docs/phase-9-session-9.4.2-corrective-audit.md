# Session 9.4.2 corrective audit

Date: 2026-09-07

Status: closed on 2026-09-08. This document remains the pre-fix baseline; final verified results are recorded in [`phase-9-session-9.4.2-test-2_7sept.md`](./phase-9-session-9.4.2-test-2_7sept.md). It supersedes any earlier claim that the five-domain API contract was a complete frontend or end-to-end pass.

## What the existing checks actually prove

| Existing check | What it proves | What it does not prove |
| --- | --- | --- |
| `test_cyber_saathi_understanding.py` | One-message intent, language, entity, and domain classification for selected phrases | Stateful follow-ups, domain-specific question progression, report readiness, UI behavior, or persistence |
| `test_cyber_saathi_five_domain_qa.py` | Five canned API conversations keep one incident, one domain, language continuity, and basic grounding | A frontend test, natural acknowledgement such as `ha bol diya`, repeated ambiguity handling, 13-domain coverage, editable reports, identity verification, submission, or dashboard tracking |
| `test_cyber_saathi_api.py` | API schema and selected transition contracts, including one corrected multi-amount case | Indian composite amounts, repeated `haan`, contextual yes/no answers, all domain state machines, or two complete browser journeys |
| `test_cyber_saathi_llm.py` | Provider fallback, structured response validation, and safety boundaries | Workflow correctness. One old test explicitly expects a financial progress follow-up to call the LLM, which conflicts with the approved deterministic workflow-state contract |
| `test_cyber_saathi_knowledge.py` | Knowledge-index validation and retrieval behavior | Conversation control, report field collection, or user-facing answer quality |
| `test_cyber_saathi_semantic_embeddings.py` | Redaction behavior for persisted semantic features | A complete RAG, conversation, report, or frontend flow |
| lint, TypeScript, and production build | Static code validity and buildability | Runtime behavior or visual/interaction acceptance |

## Confirmed defects and contract gaps

1. Amount parsing treats `2 lakh 30 hazar` as two independent amounts instead of one value, `230000`.
2. The UI displays only the first pending amount because it selects one entity with `find`.
3. An ambiguous-amount confirmation can return the same assistant message after every `haan`; the state does not record the expected answer or clarification attempt.
4. `ha bol diya`, `kar diya`, and similar short acknowledgements are not interpreted against the last question. They can fall through to generic LLM guidance.
5. The conversation state stores only `pending_question_incident_id`; it does not store the expected answer type, question key, accepted answer shape, or attempts.
6. Domain classification exists for 13 named domains plus Other/Unknown, but specialised multi-step follow-up state machines do not exist for all of them.
7. Several domains use the same generic fallback question, so classification can pass while the actual help remains generic.
8. The LLM can currently control progress wording on paths that must be deterministic, allowing repeated 1930/CERT guidance to replace the next missing question.
9. RAG retrieval proves that a source can be found, not that the source is appropriate for the current workflow stage.
10. Source cards can dominate the answer even when the user needs a direct next question; retrieval output must remain supporting context.
11. Language detection and response-language continuity are not verified through long Hinglish conversations.
12. Report readiness can expose a handoff after only a protective action, before the required reporting checklist has been intentionally collected or marked unavailable.
13. The incident report packet has not been proven to provide an actionable Open/Edit report control in a real browser journey.
14. The report handoff is held in module memory; a refresh can lose the Cyber Saathi prefill and attachments.
15. The existing form can edit a guest draft, but the Chat-to-draft bridge has not been proven persistent across navigation/refresh.
16. Earlier routing sent an identified user to Aadhaar verification before opening and reviewing the report. The accepted order is review/edit first, final Submit second, mock Aadhaar/OTP third.
17. Autofill is only partially mapped from conversation entities and does not prove that every known value survives into editable form fields.
18. Optional unknown fields are not consistently represented as missing/unavailable without blocking report review.
19. The dashboard has draft/submitted sections, but no browser test proves that a Cyber Saathi-created draft and its submitted complaint appear there.
20. No existing automated file performs the required two end-to-end browser journeys with 5–6 natural follow-ups each.
21. No existing browser evidence proves chat → checklist → persistent draft → edit → review → Submit → mock Aadhaar → mock OTP → submission → dashboard/tracking.
22. The old five-domain result used the word `frontend` for an API-level contract and therefore created a false green result.

## Replacement test matrix

Every domain must be checked against these 13 behavior areas. Passing classification alone is not a domain pass.

1. Classification and domain stability.
2. First-response safety appropriate to the facts and urgency.
3. Specialised next question for that domain.
4. Expected-answer type stored in state.
5. Contextual short-answer interpretation.
6. Entity extraction and correction.
7. No repeated question after an accepted answer.
8. Language continuity for English, Hindi, and Hinglish where applicable.
9. RAG source relevance without source-dump replacement of workflow help.
10. Report checklist progression.
11. Prefill mapping and editable missing fields.
12. Persistence and resume behavior.
13. Safe handoff, identity boundary, submission, and tracking.

The 13 specialised routes are financial fraud, e-commerce fraud, account compromise, impersonation, identity theft, online harassment, women/child online safety, cyberstalking, phishing, malware/device compromise, misinformation, child safety, and cyber terrorism. Other/Unknown must remain a safe clarification route and must never invent a classification.

## Required focused regressions

These tests must exist and pass before a browser run:

1. `2 lakh 30 hazar`, `2 lakh 30 thousand`, `2.3 lakh`, `₹2,30,000`, `230000 rupees`, and equivalent Hinglish numeric forms normalise to one amount, `230000`.
2. A sentence containing genuinely separate loss and requested-payment amounts remains ambiguous and displays both values.
3. First ambiguous `haan` does not confirm either value; a second `haan` does not append the identical assistant turn and instead requests numeric input in a distinct way.
4. A corrected numeric amount replaces the ambiguity, becomes the only pending loss amount, and can be confirmed once.
5. After the assistant asks whether the bank was contacted, `ha bol diya` records that action and moves to the next missing question without an LLM call.
6. After a bank freeze/protection question, `mene account freeze karvadiya bank se ab?` records protection and asks for the next report fact.
7. English, Hindi, and Hinglish replies remain in the user's active language throughout at least six turns.
8. Representative multi-turn state tests cover every specialised domain and assert question progression, not just labels.
9. The LLM may phrase a bounded answer but cannot mutate confirmed facts, expected-answer state, readiness, identity order, or handoff routes.
10. Report readiness is achieved only from deterministic facts/checklist status, never because the model says the report is ready.

## Required real browser verification

Browser testing starts only after the focused backend and report-lifecycle tests pass.

### Four focused browser conversations

Use natural wording, corrections, short acknowledgements, and language changes across at least four distinct domains. Record the exact messages, rendered replies, network status, state transitions, console errors, and screenshots.

### Two complete browser journeys

Each journey must use a different domain and contain 5–6 natural follow-up answers. Each must prove:

1. Cyber Saathi identifies and keeps the incident domain.
2. It asks one relevant missing question at a time.
3. Short acknowledgements answer the question actually asked.
4. Known facts appear in a numbered report checklist.
5. Open/Edit report opens the existing editable report form.
6. Conversation values are prefilled and editable.
7. The draft survives route navigation and refresh.
8. Review occurs before identity verification.
9. Final Submit initiates mock Aadhaar and mock OTP for identified reporting.
10. Successful OTP completes submission exactly once.
11. The complaint appears in the user dashboard and opens tracking.

## Honest pass rule

Do not use `PASS` for an unexecuted gate. API tests are labelled API tests, build checks are labelled build checks, and browser journeys are labelled browser journeys. A final frontend verdict requires the recorded browser evidence above. Partial work remains `INCOMPLETE` with the exact failing step and observed output.
