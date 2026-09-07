# Sahajomy web, backend, and mobile parity audit

This audit treats the React frontend as the functionality reference, the registered FastAPI router graph as the contract and permission authority, and the approved mobile screens as the Flutter presentation reference.

## Scope inspected

- React routes and page components under `D:/Projects/sahajomy-platform/frontend/src`
- FastAPI routers, schemas, dependencies, and document services under `D:/Projects/sahajomy-platform/backend/app`
- Flutter routes, repositories, pages, upload flows, and document utilities in this project
- Customer, Cargo Company, Sourcing Agent, Super Admin, public, and shared-link workflows

The reproducible row-level output is in `web-mobile-functionality-matrix.csv` and `web-mobile-functionality-matrix.json`. Run `python tool/audit_web_mobile_parity.py` to regenerate it.

## Major React modules reviewed

- Public: landing, service information, Agizisha catalogue/storefront/product, public containers, FCL request, registrations, shared batches, receipt verification, labels, legal, help, and support.
- Customer: dashboard, containers, seaBookings and detail, shipment orders, air cargo, China addresses, tracking, sourcing orders, warehouse access, invoices, receipts, packing lists, and notifications.
- Cargo Company: dashboard, seaBookings, containers, warehouses, shipment orders, packing lists, consolidated packing lists, receipts, invoices, customs documentation, manual intake, air cargo, FCL, tracking, automation, staff, branches, and finance.
- Sourcing Agent: dashboard, products, batches, orders, packing lists, financial documents, containers, seaBookings, air cargo, labels, financials, and notifications.
- Super Admin: dashboard, users, operators, approvals, governance, service controls, goods classification, seaBookings, tracking, automation, finance, audit, sourcing-agent review, and notifications.

## Document contract findings

- Official invoice, receipt, packing-list, and consolidated packing-list files are generated or streamed by FastAPI. Flutter must open and share those bytes and must not recreate totals or official layouts.
- Customer seaBooking documents are exposed through seaBooking detail plus authenticated invoice and receipt PDF streams.
- Cargo receipt rows carry `receipt_id` and `sea_booking_id`; the list is wrapped in a `receipts` envelope.
- Cargo invoice list rows are unpaid seaBooking candidates. Generating an invoice creates the authoritative invoice record and document.
- Customs packing lists support detail, editing while draft, duplication, finalization, cancellation, and backend PDF export.
- Sourcing-agent packing lists support backend PDF and Excel export. Existing Flutter flows already call these endpoints.
- Shipping-label endpoints return the backend printable-label model, including per-carton labels and QR payloads.

## Confirmed web/backend mismatch

`pages/customer/components/ShipmentOrderForm.jsx` calls `GET /customer/air-bookings`, but no registered FastAPI handler owns that route. The supported customer air-booking list is `GET /customer/express-air-cargo/bookings`. Mobile must use the registered endpoint.

## Contract corrections applied in Flutter

- Customer and Cargo Company sea operations now call `/seaBookings`, matching FastAPI.
- Sourcing Agent and Super Admin seaBooking browsers now use their registered `/seaBookings` routes.
- The shared list decoder supports both bare arrays and FastAPI metadata envelopes.
- Public document downloads skip account, tenant, and refresh interceptors.
- Customer invoice/receipt pages no longer display fabricated items or amounts.
- Customer and cargo documents use authenticated backend PDF streams for open/share.
- Cargo consolidated and customs packing-list screens display backend rows and export backend PDFs.
- Customer shipping labels load the backend printable-label payload and render its per-carton and QR data.

## Current verification rule

An API literal or route alone is classified as partially implemented until its screen actions, states, permissions, and backend response handling have been verified. The matrix therefore does not mark source-only matches as complete.
