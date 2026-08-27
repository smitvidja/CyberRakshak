# Submission Notes

Prepared in Session 8.2. Covers the safety/compliance checklist, the mocked-dependency
disclosure, and the two-minute demo script.

Each checklist item below records **how** it was checked, not just a tick — items that
are unverified or only partly done say so explicitly.

---

## 1. Builder Brief & safety compliance

### Honest presentation

| Requirement | Status | How it was verified |
|---|---|---|
| Not presented as an official/government-approved system | **Pass** | Searched all user-facing copy (EN + HI) for "government approved", "official government", "authorised by", "Govt. of India", "Ministry of" — no matches. |
| Prototype status disclosed in the UI | **Pass** | Persistent top-bar notice "Safe prototype – no live government verification"; footer "CyberRakshak prototype – safe, non-government demonstration"; plus an in-flow notice that it does not connect to government identity systems or use real OTP. |
| Mocked dependencies named clearly | **Pass** | Table in `README.md` and §2 below; résumé-parser mock also disclosed in `DEMO-CREDENTIALS.md`; leaderboard demo rows disclosed on the page itself. |

### Branding restrictions (`design/Read.md.txt`)

| Requirement | Status | How it was verified |
|---|---|---|
| No national emblem / official logo | **Pass** | Enumerated every image shipped in `frontend/public/`. 18 files: 10 awareness posters, 1 custom eye logo, 6 category illustrations, 1 hero image. No emblem present. |
| No political photographs | **Pass** | Same enumeration — no photographs of any real person. |
| Custom logo used in place of an official mark | **Pass** | Custom eye/network mark in the header. |

### Data safety

| Requirement | Status | How it was verified |
|---|---|---|
| Demo data fully synthetic | **Pass** | 11 demo identities are fabricated names with `99000000000001`-style IDs (not valid Aadhaar) and `@demo.cyberrakshak.local` addresses. Demo résumés are generated, and footer-marked "not a real person". |
| No real Aadhaar / PAN / OTP verification | **Pass** | Mock identity service only; no external calls. |
| No secrets committed | **Pass** | Only `.env.example` files are tracked; git history contains no `.env`. Examples hold placeholders only. |
| Anonymous reporting attaches no identity | **Pass** | Enforced server-side and covered by tests asserting `user_id is None` after an anonymous submission, and that public tracking exposes no identity or narrative. |
| Authorization enforced server-side | **Pass** | Test suite covers 401 for missing/malformed tokens across protected endpoints, 403 for cross-user and cross-role access. |

### Scope constraints

| Requirement | Status |
|---|---|
| No FIR workflow, police hierarchy, or investigator assignment | **Pass** — not implemented |
| No payment handling | **Pass** — not implemented |
| No live government/private system integration | **Pass** — none |

---

## 2. Mocked dependency disclosure

Stated plainly so a reviewer is never misled about what is real:

1. **Identity verification (Aadhaar/eKYC)** — mocked. A fixed set of synthetic demo
   identities; no UIDAI or government system is contacted.
2. **OTP delivery** — mocked. No SMS is sent; OTPs are fixed per demo identity. The
   API returns only a masked mobile number, never the OTP.
3. **Résumé parsing** — static mock. The same synthetic sample data is returned
   regardless of the uploaded file. No text extraction or AI. The human review-and-
   confirm step that follows is real, and nothing is written to the profile until
   the user confirms.
4. **Authority/police updates** — not implemented. No real authority receives
   anything.
5. **Admin decisions** — real and authorization-enforced, but made inside this
   prototype and via API only (no admin UI). A submitted warrior report therefore
   remains "Under Review" during a demo.
6. **Leaderboard peers** — synthetic sample rows, disclosed on the page. Only the
   signed-in warrior's own row reflects real activity.

**What is genuinely real:** complaint creation/submission/tracking with real
persistence, evidence upload with validation and ownership checks, reference-number
generation, the full warrior application lifecycle, role/ownership authorization,
audit logging, notifications, and English/Hindi throughout.

---

## 3. Two-minute demo script

Prioritises the citizen reporting journey, as required.

**Before you start:** backend and frontend running; database migrated **and seeded**;
browser at `http://localhost:3000/en` (or the deployed URL); pick an unused identity
from `DEMO-CREDENTIALS.md`.

| Time | Action | Point to make |
|---|---|---|
| 0:00–0:15 | Open the home page. | Bilingual public-service entry, six clear report categories, helpline 1930 visible. Note the "Safe prototype" banner — honest about what this is. |
| 0:15–0:30 | Click **Women and Child Safety** → **Report anonymously**. | Anonymous reporting is a first-class path, not an afterthought — no identity is collected at any point for this category. |
| 0:30–1:00 | Fill the incident form, attach a small file as evidence. | Validation is server-side; evidence is stored outside the database with only metadata persisted. |
| 1:00–1:20 | Review and submit. Show the reference number. | The complaint is genuinely persisted; the reference number is real and immediately usable. |
| 1:20–1:35 | Go to **Track Complaint**, paste the reference number. | Public tracking works without logging in, and deliberately exposes no identity or incident narrative. |
| 1:35–1:50 | Switch language to **Hindi** on the same screen. | Complete bilingual coverage, not partial translation. |
| 1:50–2:00 | Open **Learning Corner**. | Ten awareness posters with the story of each scam and what to do — the preventive half of the product. |

**Optional extension (+60s) — Cyber Warrior:** verify with an unused demo identity →
profile → résumé upload (use a PDF from `demo-assets/resumes/`) → review the parsed
details → submit application → dashboard. Say plainly that the parsing is mocked.

**Demo cautions**

- Use a **fresh, unused** demo identity for the warrior journey — an identity that has
  already applied goes straight to its dashboard (correct returning-user behaviour,
  but it skips the registration story). `backend/scripts/check_demo_warrior_status.py`
  shows which are unused; `reset_demo_warrior_data.py <id>` frees one up.
- If deployed on ephemeral storage, upload evidence **during** the demo and open it
  immediately — files do not survive a restart (`docs/DEPLOYMENT.md` §5).
- Don't promise an admin approving the warrior application live — there is no admin UI.

---

## 4. Verified status at time of writing

| Check | Result |
|---|---|
| Backend test suite | **69 passed** |
| Frontend production build | **Clean** |
| Frontend lint | **Clean** |
| EN/HI translation parity | **In sync**, zero missing keys either direction |
| Clean-database migration | **Verified** from empty through all four migrations |
| Seed script idempotency | **Verified** — second run inserts nothing |
| Production-style boot (prod env, real secret, remote-style CORS) | **Verified** — starts, serves, allowed origin accepted, unknown origin rejected |
| All top-nav routes resolve | **Verified** — every nav target returns 200 (see note below) |
| Public-URL smoke test | **Not done** — requires deployment (Session 8.3) |

> Two dead navigation links were found and fixed during this phase. "Learning Corner"
> pointed at `#learning`, an anchor that existed nowhere on the page, and separately at
> `/{locale}/resources`, a route that has never existed. "Contact" pointed at
> `/{locale}/contact`, which returned 404 — a reviewer clicking it during evaluation
> would have hit an error page. A minimal Contact page now exists carrying only
> information that is actually true: the real 1930 helpline, links to existing flows,
> and the prototype disclosure. It deliberately contains **no** invented email address,
> office address, or support number.

---

## 5. Open risks

1. **File storage is ephemeral on most hosts** — the single most likely thing to
   surprise someone after deployment. `docs/DEPLOYMENT.md` §5 lists the three options.
2. **No admin UI** — admin actions are API-only, so warrior applications and reports
   cannot be advanced through a browser during a demo.
3. **Résumé parsing is not real** — safe as long as it is stated rather than implied.
4. **Not yet deployed** — nothing in this repository has been verified against a live
   public URL. Session 8.3 covers that once hosting exists.
