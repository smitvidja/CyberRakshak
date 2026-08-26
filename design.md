# Frontend Design System & Visual Enhancement Standard

> **Purpose:** Design source of truth for frontend implementation and visual enhancement.
>
> **Core principle:** Preserve the approved UI/UX; enhance the visual execution.

---

## 1. Design Philosophy

The approved reference designs define the **intended experience**.

The implementation should reproduce that experience faithfully while allowing professional frontend-level refinement.

### Mandatory Design Folder Inspection

The project's exact design-reference structure is:

```text
design/
├── cyber_warrior/
├── home/
└── victim_Report/
```

These **three folders are the design source of truth**.

Before making any frontend design decision, inspect:

- `design/cyber_warrior/`
- `design/home/`
- `design/victim_Report/`

Inside **each of these three folders**, inspect **all relevant `.png`, `.jpg`, and `.jpeg` reference images**.

Do not inspect only one folder or one screenshot. The complete visual system must be understood from the references across all three folders.

Do not inspect only one screenshot or assume that one image represents the complete design system.

The reference images collectively define the approved visual language, including:

- Header
- Navbar
- Typography
- Font sizes and weights
- Colors
- Spacing
- Alignment
- Cards
- Buttons
- Forms
- Icons
- Images / illustrations
- Breadcrumbs
- Page composition
- Responsive patterns
- Interaction patterns where visible

### Mandatory Rule for Agents

Before implementing frontend design work:

1. Locate the `design/` directory.
2. Open `design/cyber_warrior/`.
3. Open `design/home/`.
4. Open `design/victim_Report/`.
5. Inspect all relevant `.png`, `.jpg`, and `.jpeg` files inside all three folders.
6. Compare the references to the existing implementation.
7. Use the references collectively as the visual source of truth.

**Do not select a single image and ignore the remaining references.**

If the folders or reference images cannot be found, search the repository thoroughly before proceeding. If they still cannot be found, explicitly report the missing references instead of silently inventing a design.

### The rule

> **Reference = boundary, not a limitation.**

Do not redesign the product when asked to improve its design.

Instead:

**Preserve the UI/UX → improve the visual quality → add subtle interaction polish.**

The final result should feel like the same product, same flow, and same design — but more polished, responsive, accessible, and production-ready.

---

## 2. What Must Stay Consistent

Unless explicitly instructed otherwise, do NOT change:

- Information architecture
- User journey / UX flow
- Page structure
- Navigation model
- Header structure
- CTA placement
- Form flow
- Component purpose
- Card arrangement
- Content hierarchy
- Existing functionality
- Routes / business logic
- Overall visual identity

Do not replace an approved UX pattern simply because another pattern appears more modern.

---

## 3. What Can Be Professionally Enhanced

Within the approved structure, improve:

- Typography
- Font size and weight
- Line height
- Letter spacing
- Spacing and padding
- Alignment
- Grid consistency
- Container proportions
- Icon sizing and placement
- Image sizing, cropping and presentation
- Border treatment
- Border radius
- Shadows / elevation
- Subtle color refinement
- Responsive behavior
- Accessibility
- Hover states
- Focus states
- Active states
- Transitions
- Micro-interactions
- Loading feedback
- Empty/error/success states where appropriate

These improvements must support the existing UX rather than alter it.

---

## 4. Reference-First Implementation

Before modifying a page:

1. Inspect the repository's design/reference folder.
2. Open and study the relevant reference images/assets.
3. Inspect existing shared frontend components.
4. Identify existing design tokens and patterns.
5. Determine which parts of the reference are structural and which are visual.
6. Implement using reusable components/tokens.
7. Run the application.
8. Compare the rendered result with the reference.
9. Refine visual discrepancies.
10. Only then consider the task complete.

**Do not design from memory.**

If a reference asset exists in the repository, inspect it instead of approximating it from its filename or description.

---

## 5. Visual Reference vs. Implementation Freedom

### Reference determines

- Overall composition
- Layout
- Component placement
- Navigation appearance
- Information hierarchy
- Major spacing relationships
- Visual identity
- Page proportions
- User flow

### Implementation may improve

- Exact typography sizing
- Font weights
- Spacing precision
- Alignment
- Shadows
- Borders
- Radius
- Icon treatment
- Image presentation
- Hover feedback
- Transitions
- Animation
- Responsive behavior
- Accessibility
- Micro-interactions

The goal is **high visual fidelity with higher implementation quality**, not blind pixel copying.

---

# 6. Portal Visual Identity

This is a modern Indian government cybersecurity/public-service portal.

The visual language should communicate:

- Trust
- Security
- Authority
- Clarity
- Accessibility
- Professionalism
- Modern digital public service

### Primary identity

**White + blue must remain the dominant visual language.**

Use:

- White / off-white for primary surfaces
- Deep navy for authority and headings
- Royal / portal blue for actions and interactive elements
- Very light blue / neutral tones for supporting backgrounds

Additional colors are allowed only as restrained semantic accents:

- Green → success / positive / safety states
- Amber → warnings
- Red → errors / destructive actions

Do not allow secondary colors to overpower the white-and-blue identity.

### Avoid

- Neon cyberpunk palettes
- Excessive black backgrounds
- Hacker/glitch aesthetics
- Excessive gradients
- Heavy glassmorphism
- Excessive glow effects
- Random decorative colors

Cybersecurity should be communicated through **trust, precision and modernity**, not visual clichés.

---

# 7. Typography

Typography is a major part of visual fidelity.

Use the project's existing font configuration unless the approved reference explicitly requires another font.

Refine where appropriate:

- Font family consistency
- Font size
- Font weight
- Line height
- Letter spacing
- Heading/body contrast
- Navigation typography
- Button typography

Typography should feel:

- Clear
- Modern
- Institutional
- Highly readable

Do not introduce different fonts for different sections merely to make them feel unique.

---

# 8. Spacing & Alignment

Professional UI quality depends heavily on spacing discipline.

Maintain a consistent spacing system across:

- Header
- Navbar
- Breadcrumbs
- Hero
- Sections
- Cards
- Forms
- Buttons
- Footer

Look for opportunities to improve:

- Uneven padding
- Misaligned content
- Inconsistent gaps
- Crowded elements
- Excessive empty space
- Inconsistent container widths
- Poor vertical rhythm

Prefer existing spacing tokens over arbitrary page-specific values.

---

# 9. Cards & Surfaces

Cards should feel structured and trustworthy.

Use the established system for:

- Border radius
- Border color
- Shadow/elevation
- Internal padding
- Heading hierarchy
- Background

### Professional enhancement is encouraged

For example, a card may subtly:

- Increase elevation on hover
- Highlight its border
- Lift by a few pixels
- Transition smoothly
- Reveal a relevant icon/state

But the interaction must remain subtle.

### Do not

- Turn every card into a flashy animated component
- Add unnecessary gradients
- Add excessive glow
- Change card layout purely for visual novelty

---

# 10. Hover & Cursor Interactions

Interactive elements should provide clear feedback.

Where appropriate, add subtle effects such as:

- Card highlight when the cursor enters
- Small elevation change
- Border emphasis
- Soft background transition
- Button lift/press feedback
- Icon movement
- Link underline/colour transition
- Navigation active/hover feedback

Example principle:

> Cursor enters card → card gently responds → cursor leaves → card returns smoothly.

The animation should communicate **interactivity**, not attract attention for its own sake.

---

# 11. Animation & Motion

Animation is allowed and encouraged when it improves perceived quality or usability.

Good uses:

- Hover transitions
- Dropdown open/close
- Button state transitions
- Card hover
- Page/section entrance
- Progress indicators
- Loading states
- Image reveal
- Active navigation feedback
- Success/error feedback

Use smooth, short, restrained transitions.

### Avoid

- Constant movement
- Excessive bouncing
- Glitch effects
- Flashing
- Long animations
- Motion that delays user actions
- Animation everywhere simply because it is possible

The portal should feel **calm and premium**, not animated for the sake of animation.

---

# 12. Images & Illustrations

Images are part of the design system.

Improve where useful:

- Aspect ratio
- Cropping
- Resolution
- Positioning
- Object-fit behavior
- Spacing around imagery
- Border radius
- Subtle hover treatment

Do not replace an approved illustration or image with a different visual concept unless explicitly requested.

Illustrations should integrate naturally with the page rather than dominate the interface.

---

# 13. Icons

Use a consistent icon family.

Maintain:

- Stroke/weight consistency
- Size consistency
- Alignment
- Optical balance
- Semantic meaning

Icons may receive subtle interaction effects where appropriate.

Do not mix unrelated icon styles.

---

# 14. Navbar & Shared Shell

The global shell is especially important.

Victim/User reporting references establish the primary portal navigation language.

Other journeys, including Cyber Warrior, should use the **same visual system**.

### Navbar requirements

The navbar should:

- Blend into the light portal shell
- Use the approved light/white treatment
- Use consistent borders
- Use the approved radius
- Use the same typography
- Use consistent spacing
- Use consistent icons
- Have clear active/hover states
- Work consistently across desktop and mobile

### Critical rule

**Do not create a separate visual navbar for Cyber Warrior or another section.**

If a shared navbar component exists, reuse it.

The Cyber Warrior page may have different active navigation content, but it should still look like the same portal.

---

# 15. Responsive Design

Responsive behavior must preserve the reference experience.

Verify:

### Desktop

- Correct container width
- Balanced whitespace
- Proper alignment
- Navigation spacing
- Image proportions

### Tablet

- Natural stacking
- Appropriate spacing reduction
- Navigation adaptation
- No cramped controls

### Mobile

- No horizontal overflow
- No clipped text
- Touch-friendly controls
- Readable typography
- Proper card stacking
- Correct image scaling
- Functional navigation

Do not create an unrelated mobile design.

Adapt the same experience to the screen.

---

# 16. Accessibility

Visual enhancement must not reduce accessibility.

Maintain:

- Strong color contrast
- Keyboard navigation
- Visible focus states
- Semantic HTML
- Accessible labels
- Accessible dropdowns
- Appropriate heading hierarchy
- Touch-friendly targets
- Reduced-motion consideration where applicable

A visually impressive interface that is difficult to use is not an improvement.

---

# 17. Component Reuse

Before creating a new component, search the codebase.

Prefer:

1. Existing shared component
2. Existing design token
3. Existing utility
4. Existing page pattern
5. New component only when necessary

Do not duplicate:

- Navbar
- Header
- Footer
- Buttons
- Cards
- Inputs
- Breadcrumbs
- Typography styles
- Design tokens

unless there is a genuine functional reason.

---

# 18. Scope Discipline

When the task is a **design enhancement**, preserve functionality.

Do not casually modify:

- APIs
- Database logic
- Routes
- Authentication
- Business rules
- Form submission logic
- Existing data flow

If a visual problem can be solved through CSS/component structure, solve it there.

Do not perform unrelated refactoring.

---

# 19. Quality Bar

Do not stop at:

> "The page works."

The target is:

> **"The page works and looks intentionally designed."**

Before completion, evaluate:

- Does it match the approved reference?
- Does it feel like the same portal?
- Is typography polished?
- Are spacing and alignment intentional?
- Are images and icons visually balanced?
- Do interactive elements respond naturally?
- Are animations subtle and purposeful?
- Does the white-and-blue identity remain dominant?
- Does the page work cleanly on mobile?
- Did any UX or structure change unintentionally?

---

# 20. Definition of Done

A frontend design enhancement is complete when:

- [ ] Relevant design references were inspected
- [ ] Existing shared components were inspected
- [ ] Existing design tokens were reused
- [ ] Approved UI/UX structure was preserved
- [ ] Typography was refined consistently
- [ ] Spacing and alignment were refined
- [ ] Images and icons were visually polished
- [ ] White-and-blue visual identity was preserved
- [ ] Hover/focus/active states were considered
- [ ] Appropriate micro-interactions were added
- [ ] Animation remains subtle and purposeful
- [ ] Responsive behavior was verified
- [ ] Accessibility was preserved
- [ ] Existing functionality still works
- [ ] Rendered UI was visually compared with references
- [ ] No unrelated redesign was introduced

---

# Golden Rule

> **Preserve the approved UI/UX; enhance the visual execution.**

> **Do not redesign the experience. Make the existing experience look and feel professionally finished.**

**Inspect → Understand → Reuse → Enhance → Render → Compare → Refine**
---

# 21. Phase 5 Lessons That Must Not Repeat

These lessons are permanent project memory for Phases 6, 7, and 8.

## 21.1 The Design Folder Is the Acceptance Contract

The relevant folder under `design/` is the project owner's **GOD document** for frontend scope.

- `design/home/` governs the home experience.
- `design/victim_Report/` governs the citizen/victim journey.
- `design/cyber_warrior/` governs the complete Cyber Warrior journey.

A prompt can identify the current session, but it may accidentally omit a screen, state, control, or interaction. If the relevant design folder visibly contains that requirement, the implementation must include it unless it conflicts with a higher-priority security or architecture rule.

The approved safety exception remains mandatory: do not reproduce official government emblems, official portal branding, political photographs, live-government claims, or real identity integrations. Replace those assets with neutral CyberRakshak branding and safe imagery while preserving the reference composition, hierarchy, density, and interaction model.

## 21.2 Inventory Before Implementation

Before editing frontend code:

1. Enumerate every image in the relevant design subfolder.
2. Order the images by their step names.
3. Build a coverage matrix containing reference image, route, screen/component, interaction, frontend state, API/service, persistence/storage, mock boundary, and verification method.
4. Mark each row as existing, partial, missing, or blocked.
5. Implement missing functional states as well as visible layouts.

Do not start from the current UI and merely improve what happens to exist. Start from the complete reference journey and compare the current product against it.

## 21.3 Screenshots Are Functional Requirements

A reference image is not only a color or styling guide. It can define:

- A required page or dashboard.
- The order of a multi-step journey.
- Required previous, next, save, edit, review, and submit actions.
- Form fields and upload placement.
- Status stages, pending states, and future stages.
- Card click behavior and navigation destinations.
- Breadcrumb hierarchy.
- Side panels, support bands, notices, and success guidance.
- Empty, processing, under-review, success, tracking, and detail states.

If an element looks interactive, verify the full surface behaves correctly. Do not make only the button work when the card or image is also presented as an entry affordance.

## 21.4 Visual Fidelity Must Be Measured

The following Phase 5 failures must not recur:

- Replacing a supplied portal composition with a generic dashboard or centered-card layout.
- Using oversized headers or excessive whitespace that pushes required content below the first desktop viewport.
- Failing to show all six report categories together at the intended desktop breakpoint.
- Stretching a sprite/contact sheet into the wrong aspect ratio instead of using individual assets with `object-contain` in stable media slots.
- Omitting reference icons, action rails, update panels, learning strips, side guidance, or support bands.
- Treating typography, spacing, density, card proportions, and visual hierarchy as optional polish.
- Leaving breadcrumbs generic instead of reflecting the real journey, such as `Home / Dashboard / Report Incident`.

Desktop comparison must include at least `1366x768` and `1920x1080`; mobile must confirm readable stacking, touch targets, no overflow, and no clipped controls.

## 21.5 Journey Completeness Comes Before Cosmetic Completion

A journey is not complete because its first form submits.

For every in-scope journey, verify:

- Entry and eligibility/choice state.
- Identity or anonymous branching.
- Profile or onboarding state.
- Dashboard/home state.
- Every form step in order.
- Evidence at the reference-defined step.
- Review and editable sections.
- Declaration and submit behavior.
- Success/acknowledgement state.
- Tracking with all current and future stages visible.
- List/history surface.
- Detail surface and updates where referenced.
- Previous/back navigation and preserved data.

## 21.6 Citizen Rules That Exposed the Gaps

The following implemented rules are regression requirements:

- Anonymous reporting is available only for Women and Child Safety.
- Women and Child Safety offers anonymous and identified paths.
- Every other report category offers only the identified/profile path.
- Anonymous complaints never attach a user identity.
- Category images, titles, and descriptions open the category entry screen; direct CTA buttons retain their intentional shortcuts.
- Synthetic identity verification uses backend-held 14-digit demo IDs and fixed demo OTPs; credentials belong in `DEMO-CREDENTIALS.md`, not in public UI.
- Identity lookup checks the synthetic record and linked masked mobile before OTP verification.
- Verified profile data is auto-filled. Name and registered mobile remain immutable; permitted profile fields and alternate mobile remain editable.
- The citizen dashboard is a required journey state, not an optional decorative page.
- Incident evidence is selected on the incident-writing screen and persists through the same save/continue action.
- Future incident dates are rejected in both frontend and backend validation.
- People Involved includes Myself, My Child (Minor), and Someone Else, plus an explicit known/unknown suspect branch.
- Affected-person values persist through API, service, database, review, and subsequent reads.
- Tracking always renders Submitted, Under Review, Investigation, and Action/Resolution, even when later stages are pending.
- My Reports, tracking detail, review, and success screens must remain connected to real persisted complaint data where the architecture provides it.

## 21.7 Mocked Does Not Mean Fake-Looking or Disconnected

Mock only unavailable external dependencies, not the product workflow.

- Aadhaar/eKYC, OTP delivery, government responses, authority decisions, and live integrations remain synthetic.
- UI interactions, backend endpoints, validation, persistence, ownership, evidence metadata, resume upload/review, application submission, tracking state, and dashboard logic should work genuinely where planned.
- Never expose real credentials or sensitive personal data.
- Never show demo credentials in public product UI unless a later requirement explicitly changes that decision.
- Clearly label prototype boundaries without allowing warnings to dominate the page design.

## 21.8 Architecture and Data Must Follow the Visual Flow

When a reference exposes missing behavior:

1. Map it to the existing route and component boundary.
2. Check existing API, service, repository, model, and migration contracts.
3. Reuse existing abstractions.
4. Add the smallest documented contract change only when persistence is genuinely required.
5. Apply migrations before database-backed tests.
6. Test authorization, ownership, validation, and anonymous separation server-side.

Do not encode persistent business data only in presentation state, create duplicate services, or bypass established module boundaries to make a screenshot appear correct.

## 21.9 Verification Must Prove Completion

Do not interpret a command banner, silence, or a still-running process as success.

- Lint must exit successfully.
- A production build must finish TypeScript, page generation, and finalization successfully.
- Database-backed tests require healthy PostgreSQL connectivity and the current Alembic head.
- Focused tests run first; the full relevant suite runs after the focused failure is fixed.
- Local frontend and backend processes must be refreshed after a verified build or backend contract change.
- Required routes and APIs must return successfully from the refreshed processes.
- Visual comparison is separate from lint, build, route, and API checks.
- If browser/screenshot tooling is blocked, report that limitation honestly; do not claim visual parity from compilation alone.
- Review `git diff --check`, changed-file scope, and architecture impact before commit.
- Commit and push only after the reference, behavior, automated checks, and localhost checks pass.

## 21.10 Work Efficiently Under Time Pressure

- Continue from current repository state; do not redo completed work.
- Diagnose the exact failing layer before changing code or dependencies.
- Do not repeatedly run a hanging command or repeat Git access checks without an actual failure.
- Do not reinstall healthy dependencies.
- Stop only processes confirmed to belong to this project.
- Keep each change focused and avoid unrelated refactors.
- Use a screen/route/contract matrix to prevent repeated visual iterations.
- Report blockers immediately and precisely rather than spending time on silent retries.

---

# 22. Mandatory Frontend Session Gate

Before every frontend session commit and push, complete this checklist:

- [ ] Reopen `design.md`.
- [ ] Enumerate the complete relevant design subfolder.
- [ ] Identify every image in the session's scope.
- [ ] Confirm every referenced screen has a route or intentional state.
- [ ] Confirm every visible control and card affordance has the expected interaction.
- [ ] Confirm previous/next navigation preserves the journey and data.
- [ ] Confirm frontend state, API, backend service, database/storage, and mock boundaries agree.
- [ ] Confirm all required intermediate, processing, empty, error, review, success, tracking, and detail states exist.
- [ ] Compare the rendered desktop and mobile UI against the exact references.
- [ ] Confirm safe CyberRakshak substitutions preserve the original composition.
- [ ] Run lint, production build, relevant tests, and route/API checks.
- [ ] Refresh localhost processes and inspect the final build.
- [ ] Review changed files and confirm no unrelated journey or architecture was modified.

**A session is not complete and must not be pushed while any in-scope reference row is missing, disconnected, visually unverified, or functionally incomplete.**

---

# 23. Phase 6 Cyber Warrior Non-Negotiable Coverage

For Phase 6, `design/cyber_warrior/` is the mandatory final UI/UX, design, state, and feature acceptance contract after **every session**.

At the start and end of each Phase 6 session:

1. Re-enumerate the complete folder.
2. Identify the exact Step images owned by the session.
3. Compare every implemented route/state to those images.
4. Verify the complete interaction and data flow, not only the visual shell.
5. Do not commit or push until all session-owned reference rows pass.

The current folder defines this journey coverage:

- Step 0: Become a Cyber Warrior.
- Step 1.1: Identity verification.
- Step 1.2: Synthetic identity auto-fill.
- Step 2: Resume upload and application details.
- Step 3: Extracted/application review and submit.
- Step 4: Application submitted / under review.
- Step 5: Cyber Warrior dashboard.
- Steps 6-9: Cybercrime report identification, description, evidence, review, and submit.
- Steps 10-11: Report submission acknowledgement states.
- Step 12: Track My Report.
- Step 13: Report details and authority updates.
- Step 14: Cyber Warrior profile.
- Step 15: Leaderboard.
- Step 16: Badges and rewards.
- Step 17: Resources.

Additional Phase 6 rules:

- Resume parsing output is untrusted until the user reviews, edits, and confirms it.
- Do not invent live government identity verification, administrative review, authority decisions, or unavailable external integrations.
- Do not implement dashboard cards without their referenced destinations and states.
- Do not postpone required Step images merely because a phase prompt summarizes them incompletely.
- Do not create a second frontend architecture, API client, auth flow, upload abstraction, or tracking implementation.
- Use the existing CyberRakshak shell and safe branding while matching the Cyber Warrior reference layout and hierarchy.

At Phase 6 completion, produce a final Step 0-17 coverage audit before push. Phase 7 must then test those complete journeys end to end; Phase 8 must harden and deploy them without reducing their design fidelity or behavior.
