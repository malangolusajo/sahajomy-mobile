# Sahajomy Mobile App Prototype

Last reconciled with the web platform and FastAPI backend: **2 September 2026**
at commit `6dc84cc`.

This folder is the approval and implementation-handoff package for Sahajomy's Android-first mobile app. It remains deliberately pre-Flutter: HTML previews are used to review flows and visual direction before native implementation starts.

## What is included

- `html-previews/` — 125 standalone, browser-ready mobile screens covering every current public, shared, Customer, Cargo Admin, Sourcing Agent, and Super Admin route, plus supporting flow states.
- `design-system/` — touch, typography, color, layout, scanner, QR, status, and accessibility rules.
- `flutter-plan/` — current Flutter architecture, navigation, API mapping, authentication, deep-linking, entitlement, and delivery plan.
- `api-contracts/` — mobile-facing API integration notes. The backend remains the source of truth.
- `CURRENT_PLATFORM_AUDIT.md` — dated parity review against the current React routes and FastAPI APIs.
- `GENERATED_SCREEN_INVENTORY.md` — complete current-route-to-preview matrix.
- `scripts/generate_current_previews.mjs` — reproducible generator for the 62 route previews added during the current-platform reconciliation.
- `assets/` — handoff location for approved production assets.

## Review locally

Open any `.html` file in `html-previews/` directly in a browser. The newly generated previews use embedded CSS and work offline; some original previews use the Tailwind CSS CDN and need internet access for their utility styling. They contain no React, Flutter, build step, account data, or backend dependency.

The **Prototype states** controls demonstrate loading, empty, and error treatments where present. New warehouse previews additionally demonstrate entitlement-disabled, expired-code, and handover-confirmation states.

## Current role coverage

- **Public — 31 previews:** landing, Agizisha discovery, logistics services, help, legal, warehouses, receipt verification, staff invitation, and company/agent registration.
- **Shared — 4 previews:** workspace selection, authenticated product detail, and air/sea shipping labels.
- **Customer — 26 previews:** authentication/MFA handoff, shipping, sea bookings, orders, documents, profile, Agizisha, air cargo, China addresses, warehouse parcel access, and collection QR/PIN.
- **Cargo Admin — 21 previews:** dashboard, warehouses, containers, sea bookings, receipts, four-part documentation workspace, device-based warehouse operations, finance, staff/branches, billing, air cargo, shipments, FCL, and tracking.
- **Sourcing Agent — 24 previews:** approval, storefront, Agizisha orders, batches, products, financials, packing lists, sea bookings, China addresses, air cargo, and tracking.
- **Super Admin — 19 previews:** dashboard, users, agents, cargo administrators, companies, bookings, approvals, goods, commission, audit activity, tracking, subscriptions, and costs.

The route matrix maps every current non-redirect React route to a preview and identifies redirect-only routes that intentionally reuse their destination screen. Additional files cover important subflows and UI states that do not have separate web URLs.

## Current platform rules carried into mobile

- FastAPI under `/api/v1` remains authoritative; mobile never duplicates eligibility, pricing, RBAC, payment, or status-transition rules.
- OTP authentication uses platform-secure session storage and privileged roles complete authenticator MFA when required.
- Account role remains stable while active personal/operational/company workspace, company role, branch, and permissions can change.
- Cargo-company workspaces have no public Home/landing destination.
- Existing and new staff receive invitation email and gain company access only after identity-matched acceptance.
- Scanned warehouse links return an authenticated customer to the intended warehouse after login.
- Warehouse automation is a server-enforced Cargo Admin entitlement. Manual cargo intake remains available when automation is disabled.
- Warehouse access QR values contain only opaque access URLs. Collection QR/PIN values are short-lived, single-use, and become `Collected` only after Cargo Admin confirmation.
- Camera and label-image scanning always provide immediate manual fallback.
- A matched label does not silently mutate data: staff confirms receipt, then the server creates the canonical intake/parcel, links the booking, updates Shipment Order tracking/location/status, and notifies the customer.
- Notifications use compact rows: one-line title, two-line message, short timestamp, touch swipe delete, and an accessible visible alternative.

## Approved booking interaction

The Sea and Air booking previews now use the same compact, state-driven flow for Customer and Sourcing Agent roles:

1. **Choose service** — show three useful recommendations first, then a searchable, incrementally loaded operator list that remains usable with 1,000+ services.
2. **Cargo details** — selecting an operator completes step one, prepares that operator's China address, and opens only fields required by the selected cargo mode.
3. **Review** — continuing from details does not create a booking. It opens a complete summary and the final **Confirm booking** action. Customer Sea shows only the supplier shipping mark with a path to **My China Addresses**, avoiding a duplicate full-address section.

Deep links carrying a container, Cargo Admin, or warehouse identifier must restore the relevant selection and progress state. After successful confirmation all three steps are checked and the review becomes the completed booking summary.

Regenerate the six interactive booking previews with:

```bash
node scripts/generate_booking_previews.mjs
```

Regenerate and validate current route/design/API parity with:

```bash
node scripts/generate_current_previews.mjs
node scripts/validate_current_handoff.mjs
```

## Approval boundary

Do not treat these HTML files as production code. Flutter implementation should begin only after the relevant flow previews and the current parity matrix have product approval. Backend endpoints, schemas, and tests in the main repository remain the implementation source of truth.

## Copying this package

Copy the entire `Sahajomy-Mobile-App` folder to another computer. No package installation is required to review the prototype files.
