# Sahajomy Mobile App Prototype

Last reconciled with the web platform and FastAPI backend: **20 August 2026**.

This folder is the approval and implementation-handoff package for Sahajomy's Android-first mobile app. It remains deliberately pre-Flutter: HTML previews are used to review flows and visual direction before native implementation starts.

## What is included

- `html-previews/` — 104 standalone, browser-ready mobile screens covering every current public, shared, Customer, Cargo Admin, Sourcing Agent, and Super Admin route, plus supporting flow states.
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

- **Public — 26 previews:** landing, Agizisha discovery, public logistics services, help, legal, warehouses, receipt verification, and registration.
- **Shared — 3 previews:** authenticated product detail plus air and sea shipping labels.
- **Customer — 24 previews:** authentication, shipping, reservations, orders, documents, profile, Agizisha, air cargo, China addresses, warehouse parcel access, and collection QR/PIN.
- **Cargo Admin — 15 previews:** operational dashboard, warehouses, containers, reservations, receipts, documentation, manual and automated intake, customers, air cargo, shipments, FCL, and tracking.
- **Sourcing Agent — 22 previews:** approval, storefront, Agizisha orders, batches, products, financials, packing lists, container reservations, air cargo, and tracking.
- **Super Admin — 14 previews:** dashboard, users, agents, operators, approvals, goods classification, reservations, commission, audit activity, tracking, settings, alerts, and warehouse-automation entitlements.

The route matrix maps every current non-redirect React route to a preview and identifies redirect-only routes that intentionally reuse their destination screen. Additional files cover important subflows and UI states that do not have separate web URLs.

## Current platform rules carried into mobile

- FastAPI under `/api/v1` remains authoritative; mobile never duplicates eligibility, pricing, RBAC, payment, or status-transition rules.
- OTP authentication uses access and refresh tokens stored in platform-secure storage.
- Scanned warehouse links return an authenticated customer to the intended warehouse after login.
- Warehouse automation is a server-enforced Cargo Admin entitlement. Manual cargo intake remains available when automation is disabled.
- Warehouse access QR values contain only opaque access URLs. Collection QR/PIN values are short-lived, single-use, and become `Collected` only after Cargo Admin confirmation.
- Camera and label-image scanning always provide immediate manual fallback.

## Approval boundary

Do not treat these HTML files as production code. Flutter implementation should begin only after the relevant flow previews and the current parity matrix have product approval. Backend endpoints, schemas, and tests in the main repository remain the implementation source of truth.

## Copying this package

Copy the entire `Sahajomy-Mobile-App` folder to another computer. No package installation is required to review the prototype files.
