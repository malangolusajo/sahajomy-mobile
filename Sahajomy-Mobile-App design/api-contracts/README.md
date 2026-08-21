# Mobile API Contract Notes

Base path: `/api/v1`. Authoritative request/response schemas remain in FastAPI; these notes define the mobile sequence and sensitive-data handling.

## Warehouse automation status

`GET /cargo_admin/warehouse-automation/status`

- `enabled` controls automated tools for the current Cargo Admin.
- `warehouses[]` supplies UUID, name, and whether an access QR is active.
- A disabled state keeps Manual Intake available.

## Warehouse customer access QR

- Generate/rotate: `POST /cargo_admin/warehouse-automation/warehouses/{warehouse_id}/access-token`
- Revoke: `DELETE /cargo_admin/warehouse-automation/warehouses/{warehouse_id}/access-token`
- The raw access token is returned only on generation and is represented as the returned HTTPS `access_url` QR.
- Do not persist the raw token after the user leaves the generation screen.

## Assisted intake

1. `POST /cargo_admin/warehouse-automation/intake/match`
   - request: `warehouse_id`, `scan_text`
   - response: confidence, duplicate flag, extracted values, suggested Cargo Customer and optional reservation/air-booking linkage
2. Staff reviews and edits all values.
3. `POST /cargo_admin/warehouse-automation/intake/confirm`
   - requires warehouse/customer UUIDs, cargo type, item name/description, carton count and non-negative weight
   - accepts scan/barcode/assisted-scan intake method and optional confirmed booking link
   - `409` means duplicate/conflicting parcel
4. Update release eligibility with `PATCH /cargo_admin/warehouse-automation/intakes/{intake_id}/collection-readiness`.

The mobile client must never silently confirm medium/low-confidence suggestions.

## Customer warehouse parcels

`GET /customer/warehouse-access/{opaque_token}` requires a customer access token and returns:

- warehouse UUID/name
- only that authenticated customer's active parcels in that warehouse
- server-derived `eligible_for_collection`

The app must not add customer IDs to this request or attempt client-side ownership filtering.

## Collection request

`POST /customer/warehouse-access/{opaque_token}/collection-requests`

```json
{ "intake_ids": ["uuid", "uuid"] }
```

Success returns a collection request UUID, raw collection code, six-digit PIN, UTC `expires_at`, and parcel count. Render the raw collection code as QR and the PIN as text. Keep both in memory only.

Important errors:

- `404` — selected parcel not owned/found or warehouse access invalid
- `409` — unpaid/not ready, already collected, or active request already exists
- `410` — code expired
- `429` — rate limited

## Cargo Admin verification and handover

1. `POST /cargo_admin/warehouse-automation/collection/verify` with exactly the scanned `code` or entered `pin`.
2. Show the returned parcels, weights, payment states, parcel count, and expiry.
3. After physical handover confirmation, call `POST /cargo_admin/warehouse-automation/collection/{request_id}/confirm` with the same credential.
4. Never automatically retry confirmation after timeout; first re-verify state.
5. Treat `409` as used/cancelled/ineligible and `410` as expired.

## Super Admin entitlement

- List: `GET /super_admin/warehouse-automation/cargo-admins`
- Set: `PUT /super_admin/warehouse-automation/cargo-admins/{cargo_admin_id}` with `{ "enabled": true|false }`

The flag is future-billing-ready but is not a mobile subscription or payment API.
