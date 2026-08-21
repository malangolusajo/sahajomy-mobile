# Current Platform Audit — 20 August 2026

## Source of truth reviewed

- React route inventory in `frontend/src/routes/AppRoutes.jsx`
- Role navigation in `frontend/src/components/layout/navConfig.js`
- FastAPI routers under `backend/app/api/v1`
- Current warehouse-automation models, migration, API, UI, and tests

This audit distinguishes platform parity from preview count. The reconciled package now maps every current non-redirect React route to a standalone HTML preview; additional previews cover important subflows without their own URL. See `GENERATED_SCREEN_INVENTORY.md` for the route matrix.

## Changes since the original mobile prototype

### Customer

The current platform includes dashboard, containers, reservations and detail, orders and shipment-order detail, Agizisha catalogue, Express Air Cargo, reusable China addresses, tracking, authenticated warehouse access, and multi-parcel collection QR/PIN. Legacy customer batch URLs redirect to the public Agizisha catalogue.

Mobile additions in this update include dedicated previews for every current Customer route, including:

- `customer-warehouse-parcels.html`
- `customer-collection-code.html`
- app-link/login-return requirements
- collection eligibility, expiry, and single-use states

### Cargo Admin

The current platform includes warehouses, containers, reservations, receipts/invoices, a unified cargo documentation workspace, manual cargo intake, customer records, customs packing lists, Express Air Cargo schedules/bookings, shipment orders, FCL, tracking, and optional warehouse automation.

Mobile additions in this update include dedicated previews for every current Cargo Admin route, including:

- `cargo-admin-warehouse-automation.html`
- explicit preservation of Manual Intake
- scan, label image, manual fallback, confidence, QR rotation/revocation, readiness, and handover requirements

### Sourcing Agent

The current platform extends beyond the seven original previews: approval state, Agizisha orders and public storefront, batches, batch financials, order detail, packing lists, containers, reservations, Express Air Cargo, receipts/invoices, and tracking are current routes. Dedicated HTML previews now cover each route while retaining the existing product and order-generation subflows.

### Super Admin

The current platform includes users, sourcing agents, operators, approvals, goods categories/types/attribute templates, reservations, commission history, audit logs, tracking, and per-Cargo-Admin warehouse-automation entitlement.

Mobile additions in this update include dedicated previews for every current Super Admin route, including:

- `super-admin-warehouse-automation.html`
- future-plan entitlement language without in-app billing assumptions

## Critical contract decisions

1. Mobile consumes FastAPI; it does not recreate business rules.
2. Manual and automated receipt paths write to the same underlying cargo intake records.
3. Automation availability is checked server-side, not inferred from a saved device preference.
4. Customer parcel queries are derived from the authenticated identity and scanned warehouse token.
5. Collection requests accept one to fifty intake UUIDs, require paid/ready parcels, expire after 15 minutes, and are single-use.
6. Physical collection is completed only by an authorised Cargo Admin confirmation.
7. Scanned labels are hints. High/medium/low confidence must be visible and uncertain matches require staff selection.
8. Access and collection secrets are excluded from logs, analytics, crash reports, push messages, and persistent drafts.

## Native implementation parity checklist

| Area | Prototype status | Native gate |
|---|---|---|
| OTP/auth/role routing | Existing previews; plan corrected for refresh and app links | Contract and secure-storage tests |
| Customer core shipping | Existing previews | API DTO review |
| Agizisha and China addresses | Dedicated current-route previews | Product flow approval |
| Cargo manual workflow | Dedicated previews; documented as always available | Regression test against manual APIs |
| Warehouse customer access | New previews | Android app-link and IDOR tests |
| Collection QR/PIN | New preview | Expiry, replay, multi-parcel integration tests |
| Automated intake scanner | New preview | Real-device camera/image/manual-fallback tests |
| Super Admin entitlement | New preview | Role and `403` tests |
| Notifications/deep links | Existing previews; plan updated | Role-safe navigation tests |
| Downloads/uploads | Existing document patterns | Android storage/share-sheet tests |

## Preview reconciliation result

- 104 standalone HTML previews are present.
- 62 route-specific previews were generated during this reconciliation.
- All non-redirect paths in `AppRoutes.jsx` have an explicit route-to-preview mapping.
- Redirect-only and wildcard paths intentionally reuse the mapped destination preview.

## Known repository issue

The current warehouse-automation Alembic revision passes its own PostgreSQL downgrade/upgrade validation. The repository's older full empty-database migration history currently fails before reaching it because revision `195c0ab8c407` alters `warehouses` before that table exists. Mobile development should use a supported backend environment and must not attempt to compensate for database migration history.
