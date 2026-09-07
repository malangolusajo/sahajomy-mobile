# Mobile API Contract Notes

Base path: `/api/v1`. Authoritative request/response schemas remain in FastAPI; these notes define the mobile sequence and sensitive-data handling.

## Guided booking sequence

Both Customer and Sourcing Agent flows must use the same mutation boundary:

1. Fetch services: Sea uses `/customer/containers` or `/sourcing_agent/containers`; Air uses `/forwarding/air-services`.
2. When an operator is selected, call `POST /forwarding/prepare-address` with the cargo mode and the selected `container_id` or `cargo_admin_id`/`warehouse_id` pair.
3. Keep the prepared address in memory and advance to cargo details. Customer Sea Review should use its shipping mark and route full-address management to My China Addresses instead of duplicating the saved address.
4. **Continue to review** is local state only. It validates the draft and performs no booking POST.
5. **Confirm booking** performs the final mutation:
   - Customer Sea: `POST /customer/sea-bookings`
   - Sourcing Agent Sea: `POST /sourcing_agent/containers/book-cbm` or `POST /sourcing_agent/batches/{batch_id}/book-cbm`
   - Customer Air: `POST /customer/express-air-cargo/book`
   - Sourcing Agent Air: `POST /sourcing_agent/express-air-cargo/book`
6. Replace draft values with authoritative returned identifiers, pricing, status, and address data on success.

Current OpenAPI request schemas use `CreateSeaBookingRequest` for Customer Sea
and `BookCBMRequest` for both Sourcing Agent Sea endpoints. Do not generate or
retain clients with the removed legacy request-schema names.

Never retry the final POST automatically. Preserve the reviewed draft after an ambiguous timeout and require the app to reconcile booking lists before allowing another confirmation.

## Warehouse automation status

`GET /cargo_admin/warehouse-automation/status`

- `enabled` controls automated tools for the current Cargo Admin.
- `warehouses[]` supplies UUID, name, and whether an access QR is active.
- A disabled state keeps Manual Intake available.

## Workspace context

After `/auth/me`, load `GET /workspaces`. Switching workspace does not change
`user.role`. A cargo-company selection supplies company role, branch, and
permissions. Send `X-Sahajomy-Company` and optional `X-Sahajomy-Branch` only for
that company context, and clear old tenant data before the next request.

Staff invitation endpoints are under `/workspaces/staff/invitations`. Creation
must not produce membership before the emailed token is accepted by the matching
identity.

## Warehouse customer access QR

- Generate/rotate: `POST /cargo_admin/warehouse-automation/warehouses/{warehouse_id}/access-token`
- Revoke: `DELETE /cargo_admin/warehouse-automation/warehouses/{warehouse_id}/access-token`
- The raw access token is returned only on generation and is represented as the returned HTTPS `access_url` QR.
- Do not persist the raw token after the user leaves the generation screen.

## Assisted intake

1. `POST /cargo_admin/warehouse-automation/intake/match`
   - request: `warehouse_id`, `scan_text`
   - response: confidence, duplicate flag, extracted values, suggested Cargo Customer and optional sea/air booking linkage
2. Staff reviews and edits all values.
3. `POST /cargo_admin/warehouse-automation/intake/confirm`
   - requires warehouse/customer UUIDs, cargo type, item name/description, carton count and non-negative weight
   - accepts scan/barcode/assisted-scan intake method and optional confirmed booking link
   - `409` means duplicate/conflicting parcel
4. Update release eligibility with `PATCH /cargo_admin/warehouse-automation/intakes/{intake_id}/collection-readiness`.

The mobile client must never silently confirm medium/low-confidence suggestions.

Container consolidated-packing-list responses expose
`container.fill_from_booked_percentage`; clients must not expect the removed
legacy fill-percentage property.

## Device-based warehouse operations

The current branch-scoped scan pipeline is under `/cargo/warehouse-mobile`:

1. `POST /scan-events` with code/source/idempotency key returns matched,
   unmatched, or duplicate plus authoritative booking/customer context.
2. `POST /parcels` confirms receipt and creates the canonical intake/parcel,
   linked booking tracking/Shipment Order update, and customer notification.
3. `POST /booking-selection` associates selected parcels with sea, air, or
   shipment context.
4. Create a loading session, scan parcels, then complete it. Respect green,
   duplicate, amber wrong-booking, and red not-found/branch results.
5. `POST /milestones` records loaded/departed/in-transit/arrived/customs/ready
   updates and refreshes tracking and notifications.

Do not call this the “smartphone warehouse workflow.” Camera, label image, and
manual entry are capture choices; the server-confirmed operation is the feature.

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
