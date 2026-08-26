# Frontend Visual QA

This checklist is required before a frontend session that changes shared layout, forms, dashboards, tables, or status surfaces is committed.

## Reference Set

Use these visual sources for the shared foundation review:

| Reference | Shared behavior to preserve |
| --- | --- |
| design/victim_Report/Step 0 — Updated VictimUser Reporting Flow.png | Public-service header, utility bar, primary navigation, breadcrumb, and report entry hierarchy |
| design/victim_Report/Step 8 — My Reports.png | Report list/table hierarchy, status treatment, mobile list fallback |
| design/cyber_warrior/Step 5 — Cyber Warrior Dashboard.png | Sidebar behavior, metric cards, quick-action density, dashboard content order |
| design/cyber_warrior/Step 12 — Track My Report.png | Timeline sequence, status text, detail/review spacing |

Do not replace these layouts with a generic dashboard. Official emblems and political photos are excluded from the prototype.

## Local Workflow

1. Run npm run lint and npm run build from frontend/.
2. Start the frontend with npm run dev -- --port 3000.
3. Inspect /en and /hi at both required viewports.
4. For a future feature screen, inspect the route that implements the matching reference before it is committed.
5. Record any intentional mock state in the feature session handoff. Do not treat a mock state as a live government integration.

## Required Viewports

| Viewport | Size | Check |
| --- | --- | --- |
| Desktop | 1440 x 900 | Shell hierarchy, content width, cards, table columns, sidebar spacing |
| Mobile | 390 x 844 | Navigation/sidebar scrolling, text wrapping, support action reachability, list stacking |

The current foundation has no feature-screen preview route. Until a matching journey route exists, verify shared components through their responsive constraints in source and the shell routes above.

## Responsive Checklist

- The primary navigation remains reachable without overlap; horizontal scrolling is acceptable on small screens.
- Utility-bar and support-band content becomes vertical on mobile without covering adjacent content.
- Long English and Hindi labels wrap inside cards, form fields, review values, and quick actions.
- Tables use the ResponsiveDataList mobile card/list presentation.
- Sidebars use the horizontal mobile navigation treatment rather than a duplicated mobile component.
- Fixed-format controls retain stable dimensions: icon buttons are 40px, step markers are 32px, and status chips keep a minimum height.
- No card is nested inside another card except for repeated list items where the reference calls for it.

## Accessibility Checklist

- Keyboard focus is visible on links, buttons, form inputs, upload controls, and language links.
- Every input has a programmatic label, required state, optional helper text, and error association.
- Icon-only buttons require an accessible name and expose a hover/focus tooltip.
- Status chips include text; color is never the only status signal.
- File upload controls have a visible label and an error message region.
- Interactive targets use native controls or links, with no click-only non-semantic elements.
- prefers-reduced-motion is honored by shared animation.
- The English and Hindi shell renders with the correct document language.
