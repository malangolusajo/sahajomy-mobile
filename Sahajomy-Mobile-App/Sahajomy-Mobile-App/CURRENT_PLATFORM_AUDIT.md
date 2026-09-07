# Current Platform Audit — 7 September 2026

## Source of truth reviewed

- React routes in `frontend/src/routes/AppRoutes.jsx`
- Desktop/mobile navigation and workspace guards
- OTP/MFA, workspace, invitation, registration, notification, booking, tracking,
  warehouse, finance, and subscription UI/services
- FastAPI router registration and regenerated OpenAPI contract
- Focused backend/frontend tests for the current features

The Flutter handoff is reconciled with the source tree packaged on 7 September
2026. The generated API contract now contains 342 paths, 389 operations, and
163 schemas. The visual pack has 120 HTML previews and maps every current
non-redirect React route.

## Changes now represented in mobile

### One login, multiple workspaces

- Account role remains stable during workspace switching.
- Personal, sourcing-agent, legacy cargo-operations, and multiple cargo-company
  workspaces are separate app contexts.
- Company workspace supplies company role, branch, and granular permissions.
- Company/branch headers are sent only in company context; switching clears old
  tenant state before navigation.
- Cargo-company navigation has no public Home/landing destination. Dashboard or
  the first permitted operation is the entry.

### Authentication and staff access

- Privileged roles complete authenticator MFA after OTP; first setup includes QR
  and manual secret.
- Existing and new staff both receive invitation email.
- No membership/workspace access exists before identity-matched acceptance.
- Email failure rolls back invitation creation; expired, invalid, accepted, and
  wrong-account links have distinct outcomes.

### Current route model

- Sea cargo uses Customer, Sourcing Agent, and Cargo Admin Sea Bookings routes,
  replacing stale legacy page names in the original prototype.
- The Cargo Documentation Workspace has four unique destinations: Packing Lists,
  Manual Cargo Intake, Customers & Contacts, and Warehouse Automation.
- Warehouse Automation's canonical UI route is inside Documentation Workspace.
- Cargo Company now includes Financial Analytics, Staff & Branches, and Billing
  & Usage.
- Super Admin now includes Cargo Companies/Detail, Bookings, and Subscriptions &
  Costs.
- Public/shared scope now includes staff invitation, complete cargo-company
  registration, Africa service pages, and workspace selection.

### Warehouse scanning workflow

- The mobile wording is warehouse scanning/device-based warehouse operations,
  not “smartphone warehouse workflow.”
- Camera, label-image, and manual code capture are all supported.
- Scan returns matched/unmatched/duplicate, confidence, and authoritative
  booking/customer/shipping-mark context before confirmation.
- Confirmed receipt creates canonical Manual Cargo Intake/item and parcel, links
  a matched sea/air booking, updates Shipment Order timeline/location/status to
  received at warehouse, and notifies the customer.
- Loading scans detect wrong booking and duplicate/already-loaded cases.
- Milestones update tracking and Shipment Order state and notify customers.
- Manual Cargo Intake remains available when automation is disabled.

### Design consistency

- Notifications are compact: one-line title, two-line message, short timestamp,
  32px icon, unread dot, row activation, swipe delete, and accessible alternative.
- Cargo-company registration by Super Admin collects the same profile, owner,
  origins, destinations, services, capabilities, currencies, experience,
  summary, and logo information as public registration.
- Sea and Air booking retain the approved Choose service → Cargo details →
  Review → Confirm progression.

## Native implementation gates

| Area | Required Flutter proof |
|---|---|
| OTP/MFA | Secure challenge handling, QR/manual setup, refresh race tests |
| Workspace isolation | Company/branch header tests, cache purge, role stability |
| Invitations | Email/acceptance semantics, wrong identity, expiry, retry |
| Sea/Air booking | Provider/address isolation, submit lock, real references |
| Cargo permissions | Destination/action filtering plus server 403 handling |
| Warehouse scan | Real-device camera/image/manual fallback and idempotency |
| Tracking sync | Intake/loading/milestone updates and correct notification target |
| Notifications | Compact widget/golden, swipe and non-gesture delete |
| Company registration | Public/Super Admin field parity and validation |
| Release | Android/iOS builds, focused contract/widget/integration tests |

## Known contract cautions

- Some protected operations appear as `Public` in generated OpenAPI because
  dependency-based authorization is not always emitted as a security marker.
- Several success responses remain loosely typed and file endpoints may stream
  bytes despite generic OpenAPI content.
- Server authorization, prices, totals, capacity, status transitions, tenant
  ownership, tracking numbers, shipping marks, and document generation remain
  authoritative.
- Do not create one universal status enum; preserve domain-specific states and an
  unknown-value fallback.
