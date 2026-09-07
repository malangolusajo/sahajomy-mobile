# Backend → UI Addendum Mapping

| Screens | UI capability | Backend basis |
|---|---|---|
| 150–157 | FCL quote request, route/cargo/review/list/detail/cancel | `backend/app/api/v1/fcl_quote_requests.py` |
| 158–161 | Warehouse QR display/rotation/revocation UX | Cargo Company warehouse/device intake flows; privacy constraints from mobile design system |
| 162–166 | Customs dashboard, case, docs, status, release | `backend/app/api/v1/cargo_admin/customs.py` |
| 167–172 | Duplicate/low confidence/camera denied/unreadable/offline/history scanner states | Cargo Company warehouse intake + design-system scanner requirements |
| 173–175 | Collection QR/PIN verification and already-used recovery | Cargo Company collection lifecycle + single-use collection semantics |
| 176 | Sourcing product editing and dynamic attributes | `backend/app/api/v1/sourcing_agent/routes.py` product update endpoints |
| 177 | Instagram image import | `POST /sourcing_agent/batches/{batch_id}/products/import-instagram` |
| 178 | Share invoice with customer | `POST /sourcing_agent/orders/{order_id}/share-invoice` |
| 179 | Express-air shipping-label edit | `PATCH /sourcing_agent/express-air-cargo/{booking_id}/shipping-label` |

These screens are UI specifications, not backend code. Any action must still obey server-side authorization, validation, tenant scoping, idempotency, and status-transition rules.
