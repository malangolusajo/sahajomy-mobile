# Flutter Implementation Plan

Reconciled with the Sahajomy platform on **20 August 2026**. This is an implementation plan, not a second product specification. FastAPI at `/api/v1` and its RBAC, validation, pricing, payment, collection, and status rules remain authoritative.

## Proposed architecture

`lib/`

- `app/` — bootstrap, environment configuration, router, role shells, theme, app-link handling
- `core/auth/` — secure tokens, refresh serialization, logout, authenticated identity
- `core/network/` — typed HTTP client, API errors, upload/download handling, connectivity
- `core/storage/` — encrypted preferences and short-lived draft storage; never persist collection secrets beyond need
- `core/scanning/` — camera permission, barcode/QR decoding, image-label input, manual fallback
- `core/ui/` — status chips, list rows, empty/error/loading states, confirmations, accessible controls
- `features/public_catalog/` — Agizisha catalogue, product detail, agent storefront, shared batches, receipt verification
- `features/customer/` — dashboard, containers, reservations, shipment orders, tracking, Express Air Cargo, China addresses, Agizisha, warehouse access and collection requests
- `features/cargo_admin/` — dashboard, warehouses, containers, reservations, receipts/invoices, documentation workspace, manual intake, shipment orders, FCL, Express Air Cargo, tracking, warehouse automation
- `features/sourcing_agent/` — approval state, batches, Agizisha orders/storefront, products, packing lists, financials, containers, reservations, Express Air Cargo, tracking
- `features/super_admin/` — users, sourcing agents, operators, approvals, goods classification, reservations, commission, audit logs, tracking, automation entitlements
- `features/notifications/` — notification centre, unread state, WebSocket lifecycle, role-safe deep links
- `shared/` — DTOs, domain identifiers, formatting, reusable widgets

Organise each feature by `data/`, `domain/`, and `presentation/`. Prefer generated immutable DTOs and a repository boundary. UI state must not become a second business-rule engine.

## Environment and networking

- Define development, staging, and production HTTPS base URLs at build time.
- Use one API client with a 30-second default timeout and explicit longer timeouts for document upload/download.
- Attach the bearer access token centrally.
- On one `401`, serialize a single `POST /auth/refresh`, update secure storage, and replay pending requests once.
- A failed refresh clears both tokens and routes to login while preserving only a safe app-link destination.
- Do not log OTPs, tokens, PINs, warehouse access URLs, decrypted phone/email data, or uploaded labels.
- Map FastAPI `detail`, validation arrays, `409`, `410`, `422`, and `429` into actionable mobile states.

## Authentication and app links

1. Splash reads secure storage and verifies the session with `GET /auth/me`.
2. `POST /auth/send-otp` starts sign-in or registration.
3. `POST /auth/verify-otp` returns the session and authoritative role.
4. Route to the matching role shell.
5. Logout calls `POST /auth/logout` before clearing local storage where possible.
6. Support HTTPS app links for warehouse access, shipping labels, product details, shared batches, and receipt verification.
7. If an unauthenticated customer scans `/customer/warehouse-access/:token`, keep that exact destination in memory, authenticate, then return to it. Never copy the warehouse token into analytics or logs.
8. Reject a post-login destination that does not belong to the authenticated role.

## Role navigation

Keep four primary bottom destinations and place the broader route inventory under a role-aware **More** screen.

| Role | Bottom navigation | Default |
|---|---|---|
| Customer | Home, Shipments, Agizisha, More | Customer dashboard |
| Cargo Admin | Home, Operations, Documents, More | Cargo dashboard |
| Sourcing Agent | Home, Batches, Orders, More | Agent dashboard |
| Super Admin | Home, Users, Activity, More | Platform overview |

Notifications remain reachable from every top app bar and may show an unread badge. Deep links must resolve through the router only after `GET /auth/me` and role checks.

## Current API capability map

| Capability | API family | Mobile behavior |
|---|---|---|
| Auth/profile | `/auth/*` | OTP, refresh, logout, current user, profile image |
| Customer shipping | `/customer/*` | Containers, reservations, shipment orders, tracking, Express Air Cargo, China addresses |
| Public commerce | `/public/agizisha/*`, `/public/*` shared/product/receipt routes | Catalogue, product detail, storefront, shared batch, receipt verification |
| Cargo operations | `/cargo_admin/*` | Warehouses, containers, reservations, finance documents, shipment orders, tracking, FCL and air operations |
| Cargo documentation | `/cargo_admin/customers`, `/manual-cargo-intakes`, `/customs-packing-lists` | Shared customer and receipt records; preserve manual intake |
| Warehouse automation | `/cargo_admin/warehouse-automation/*` | Entitlement, QR rotation/revocation, scan match/confirm, readiness, verification/handover |
| Customer warehouse access | `/customer/warehouse-access/*` | Own parcels only, multi-select collection request, short-lived QR/PIN |
| Sourcing workflow | `/sourcing_agent/*` | Batches, products, Agizisha orders, packing lists, financials, bookings and tracking |
| Governance | `/super_admin/*` | Users, roles, approvals, goods, commission, reservations, audit and analytics |
| Automation control | `/super_admin/warehouse-automation/*` | Per-Cargo-Admin premium entitlement |
| Notifications | `/notifications/*` plus role feeds | List, read one/all, and reconnect WebSocket safely |

See `../api-contracts/README.md` for the warehouse payload sequence and response handling.

## Warehouse automation flow

### Customer

1. Scan opaque warehouse access QR.
2. Authenticate if needed and resume the app link.
3. Fetch only the current customer's parcels for that warehouse.
4. Enable selection only when `eligible_for_collection` is true.
5. Submit one or more intake UUIDs and render the returned collection QR/PIN.
6. Display the server `expires_at` timestamp as a countdown and absolute local time.
7. Never expose a direct “mark collected” action.

### Cargo Admin

1. Read automation status before showing premium tools; a `403` is still authoritative.
2. Keep Manual Intake available in all modes.
3. Scan barcode/QR or choose a label image; show manual text entry immediately if unavailable.
4. Render high/medium/low confidence and require staff confirmation. Never silently register an uncertain result.
5. Verify a customer collection QR or six-digit PIN with the backend.
6. Show parcel/payment details, then require a deliberate physical-handover confirmation.
7. Treat `409` as used/conflicting/ineligible and `410` as expired. Do not retry confirmation automatically.

### Super Admin

Show every Cargo Admin with Manual enabled and Automation enabled/disabled. Confirm entitlement changes and refresh from the server after mutation. Do not implement billing logic in the app.

## Offline and retry boundaries

- Cache read-only dashboards and catalogues with a visible stale timestamp.
- Never queue OTP verification, payment confirmation, collection-request creation, QR rotation, intake confirmation, status changes, or physical handover for background replay.
- Preserve non-sensitive form drafts locally; remove label images and extracted text after successful intake or explicit cancellation.
- Downloads may be retried by the user. Upload progress must support cancellation.

## Delivery order

1. App shell, theme, networking, secure auth, refresh, role router, app links
2. Customer containers/reservations/tracking, Agizisha, Express Air Cargo, China addresses
3. Cargo Admin operational and manual documentation workflows
4. Sourcing Agent batches, Agizisha orders, documents and financials
5. Super Admin governance
6. Warehouse QR access, collection, scan intake, and automation controls
7. Notifications, downloads/uploads, accessibility, analytics redaction, device testing

Each phase requires contract tests against FastAPI, widget tests for loading/empty/error states, and at least one Android integration test for its critical mutation flow.

## Approval gate

Do not create production Flutter screens, API clients, signing configuration, or store assets until the relevant previews are approved. When implementation begins, keep this plan synchronized with backend route changes rather than treating it as a frozen specification.
