# Functional parity implementation report

## Web functionality audited

The audit covers 98 registered React routes and 321 page/API operations across public/shared, Customer, Cargo Company, Sourcing Agent, and Super Admin modules. The matching FastAPI graph contains 365 registered operations. See `WEB_AUDIT.md` and the CSV/JSON matrix for row-level sources and contracts.

## Functional parity matrix

The matrix is deliberately conservative: a route or endpoint literal is not marked complete until its full interaction, permission, state, and response behavior has been verified.

| Role | Verified source integration present | Still requires action-level verification/implementation |
|---|---:|---:|
| Cargo Company | 51 | 45 |
| Customer | 27 | 20 |
| Public/shared | 11 | 33 |
| Shared authenticated | 1 | 4 |
| Sourcing Agent | 48 | 29 |
| Super Admin | 17 | 35 |

## Newly added mobile screens

- Cargo consolidated packing-list detail with live rows and backend PDF open/share
- Cargo customs packing-list detail with backend PDF open/share and valid draft transitions
- Cargo pre-departure checklist connected to the backend departure action
- Backend-driven customer financial-document detail
- Backend-driven customer packing-list detail
- Backend-driven customer shipping-label view with per-carton labels and QR payload

## Packing lists

- Sourcing Agent PDF and Excel export remains connected to the existing backend endpoints.
- Cargo consolidated packing lists now use the backend snapshot and PDF stream.
- Cargo customs packing lists now use backend detail, finalize, cancel, and PDF endpoints.
- Customer packing-list summaries and backend fields replace invented line items.

## Shipping labels

Customer labels now load the backend printable-label payload, including shipping mark, customer, phone, destination, carton index, packing summary, and QR data. The app supports copying and native sharing of backend values. Cargo and sourcing-agent label action parity still needs row-level completion as recorded in the matrix.

## Receipts and invoices

- Customer open/share uses authenticated seaBooking invoice and receipt PDF streams.
- Cargo receipts use the backend receipt/seaBooking identifiers and authenticated PDF stream.
- Cargo invoice candidates generate the official backend invoice before open/share.
- Flutter does not calculate totals, currency, or references.

## Downloads and sharing

PDF/Excel bytes are saved to temporary app storage, opened with a compatible installed application, and shared through the native share sheet. Duplicate taps are blocked while a request is active. Public document URLs explicitly skip auth, tenant, and refresh interceptors.

## Uploads

Existing camera/gallery/file upload implementations remain in place. Full web-action parity for manual intake, air cargo, and certain compliance/document upload paths is still listed in the row-level matrix.

## Missing parity

The audit does not support claiming zero missing parity. The largest remaining groups are:

- Cargo Company: manual intake, air schedule/booking actions, finance analytics, remaining customs editing, seaBooking filters/actions, shipment-order actions, and tracking updates.
- Customer: dashboard actions, container filters/detail actions, remaining air-cargo actions, shipment-order creation/detail, and tracking.
- Sourcing Agent: remaining batch lifecycle operations, container/seaBooking actions, air-cargo actions, and tracking.
- Super Admin: goods classification management, operator governance detail actions, user governance actions, approvals, commission settings, and tracking.
- Public/shared: smart warehouse public flows, account/activity components, shared label/product/workspace flows, and registration/support actions.

The exact required mobile action, React source, FastAPI handler, request/response, and permission note for every remaining row is in `web-mobile-functionality-matrix.csv`.

## Backend changes

No backend changes were introduced. One stale React call was identified: `GET /customer/air-bookings` has no registered handler; the supported route is `GET /customer/express-air-cargo/bookings`.

## Validation

- `flutter test`: 54 tests passed
- `flutter analyze`: no errors; existing warning/deprecation backlog remains
- `flutter build apk --debug`: succeeded
- `git diff --check`: passed
