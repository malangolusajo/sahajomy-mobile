# Sahajomy Mobile Design System

Reconciled **20 August 2026**. This touch-first system carries the current web platform's navy/coral identity into Android while favouring flat operational layouts, dividers, and compact status information over card-heavy dashboards.

## Typography

- **Font:** Inter or system sans-serif; 400 body, 600 controls, 700–800 headings.
- **Display:** 30–32px / 36–40px only for welcome and confirmation moments.
- **Screen title:** 24px / 32px, 800.
- **Section title:** 18–20px / 26–28px, 700.
- **Body:** 14–16px / 20–24px, 400.
- **Label:** 10–12px, uppercase, 700, modest tracking.
- Numeric PINs, tracking numbers, and references use a legible monospace style without shrinking below 14px.

## Color tokens

| Token | Value | Use |
|---|---:|---|
| Brand navy | `#0F3D5E` | Headers, primary ink, strong actions |
| Brand navy dark | `#0B2A40` | Pressed/dark surfaces |
| Coral | `#FF6B4A` | Primary CTA, active navigation, emphasis |
| Coral dark | `#E85A3A` | Pressed CTA and emphasis text |
| Canvas | `#F7F8FA` | App background |
| Surface | `#FFFFFF` | Sheets and inputs |
| Ink | `#0F172A` | Primary text |
| Muted | `#64748B` | Supporting text |
| Border | `#E2E8F0` | Dividers and controls |
| Success | `#059669` | Paid, ready, confirmed |
| Warning | `#D97706` | Unpaid, pending, expiring |
| Danger | `#E11D48` | Expired, failed, destructive |

Color never carries status alone; always include a text label and, where helpful, an icon.

## Spacing and layout

- 4px base: 4, 8, 12, 16, 20, 24, 32, 40, 48.
- Standard page gutter: 20px; compact devices may use 16px.
- Use full-width divided lists for repeated operational rows.
- Cards are reserved for a single grouped decision, generated QR, or confirmation summary—not every metric.
- Respect Android safe areas, keyboard insets, text scaling, and landscape camera mode.

## Controls

- Primary/secondary buttons are 52–56px high with a minimum 48px tap area.
- Destructive and irreversible actions require explicit confirmation; physical handover must state parcel count.
- Inputs are 48–52px high, labelled above, and show server validation directly below.
- Loading keeps control width stable and prevents duplicate submission.
- Disabled automation tools explain the entitlement state and link to Manual Intake where appropriate.

## Scanner and QR patterns

- Camera view has a clear close action, permission rationale, flashlight where supported, and a visible scan target.
- Camera denial, unsupported decoding, or unreadable labels immediately reveal **Enter manually** and **Choose label image**.
- After machine decoding, show extracted values and confidence before confirmation.
- Warehouse QR screens explicitly say the code contains no parcel data and provide rotate/revoke actions.
- Customer collection QR/PIN shows parcel count, countdown, absolute expiry time, single-use notice, and maximum display brightness affordance.
- Expired, already-used, or invalid codes replace the confirmation action with a clear recovery path.

## Status vocabulary

Use backend values and user-facing mappings consistently:

- Payment: `unpaid` → Payment required; `paid` → Paid.
- Collection: `not_ready` → Not ready; `ready` → Ready for collection; `collected` → Collected.
- Collection request: `requested` → Active; `used` → Used; `expired` → Expired; `cancelled` → Cancelled.
- Do not introduce additional synonyms for the same state in the mobile layer.

## Navigation and states

- Four primary bottom destinations plus a role-aware More screen.
- Top app bar includes back affordance when needed, context/role label, and notifications.
- Every data view includes loading, empty, error, offline/stale, and retry treatments.
- `403`, `409`, `410`, `422`, and `429` require distinct messages; they are not generic network errors.
- Deep-linked screens show a safe loading shell while identity and role are verified.

## Accessibility and privacy

- Target WCAG 2.2 AA contrast, 48px touch targets, semantic labels, logical focus order, and 200% text scaling.
- QR/PIN screens provide a text PIN alternative and do not announce secrets until the user requests it.
- Never place customer parcel data in warehouse QR values, screenshots, notifications, clipboard telemetry, or analytics.
- Redact phone/email values and all tokens from logs and crash reports.
