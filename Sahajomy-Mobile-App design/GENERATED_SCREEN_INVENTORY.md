# Current-Platform Route Preview Matrix

Generated from `scripts/generate_current_previews.mjs`. Every non-redirect route declared in `frontend/src/routes/AppRoutes.jsx` maps to a standalone HTML preview below.

## Newly generated route previews

| Role | Web route | HTML preview |
|---|---|---|
| Public | `/` | [public-landing.html](html-previews/public-landing.html) |
| Public | `/agizisha` | [public-agizisha-catalogue.html](html-previews/public-agizisha-catalogue.html) |
| Public | `/agizisha/product/:id` | [public-agizisha-product-detail.html](html-previews/public-agizisha-product-detail.html) |
| Public | `/agizisha/agents/:handle` | [public-agizisha-agent-storefront.html](html-previews/public-agizisha-agent-storefront.html) |
| Public | `/shared/:token` | [public-shared-batch.html](html-previews/public-shared-batch.html) |
| Public | `/verify-receipt` | [public-receipt-verification.html](html-previews/public-receipt-verification.html) |
| Public | `/privacy` | [public-privacy.html](html-previews/public-privacy.html) |
| Public | `/terms` | [public-terms.html](html-previews/public-terms.html) |
| Public | `/contact` | [public-contact.html](html-previews/public-contact.html) |
| Public | `/about` | [public-about.html](html-previews/public-about.html) |
| Public | `/how-it-works` | [public-how-it-works.html](html-previews/public-how-it-works.html) |
| Public | `/pricing` | [public-pricing.html](html-previews/public-pricing.html) |
| Public | `/faq` | [public-faq.html](html-previews/public-faq.html) |
| Public | `/warehouses` | [public-warehouses.html](html-previews/public-warehouses.html) |
| Public | `/warehouses/:warehouseSlug` | [public-warehouse-detail.html](html-previews/public-warehouse-detail.html) |
| Public | `/support` | [public-support.html](html-previews/public-support.html) |
| Public | `/support/tickets` | [public-support-tickets.html](html-previews/public-support-tickets.html) |
| Public | `/feedback` | [public-feedback.html](html-previews/public-feedback.html) |
| Public | `/cookies` | [public-cookies.html](html-previews/public-cookies.html) |
| Public | `/accessibility` | [public-accessibility.html](html-previews/public-accessibility.html) |
| Public | `/legal` | [public-legal.html](html-previews/public-legal.html) |
| Public | `/sitemap` | [public-sitemap.html](html-previews/public-sitemap.html) |
| Public | `/air-cargo` | [public-air-cargo.html](html-previews/public-air-cargo.html) |
| Public | `/public/containers` | [public-containers.html](html-previews/public-containers.html) |
| Public | `/fcl-quote-request` | [public-fcl-quote-request.html](html-previews/public-fcl-quote-request.html) |
| Public | `/sourcing-agent/register` | [public-sourcing-agent-registration.html](html-previews/public-sourcing-agent-registration.html) |
| Shared | `/label/air/:bookingId` | [shared-air-shipping-label.html](html-previews/shared-air-shipping-label.html) |
| Shared | `/label/sea/:reservationId` | [shared-sea-shipping-label.html](html-previews/shared-sea-shipping-label.html) |
| Shared | `/product/:productId` | [shared-product-detail.html](html-previews/shared-product-detail.html) |
| Customer | `/customer/reservations` | [customer-reservations.html](html-previews/customer-reservations.html) |
| Customer | `/customer/reservations/:reservationId` | [customer-reservation-detail.html](html-previews/customer-reservation-detail.html) |
| Customer | `/customer/shipment-orders/:shipmentOrderId` | [customer-shipment-order-detail.html](html-previews/customer-shipment-order-detail.html) |
| Customer | `/customer/agizisha` | [customer-agizisha.html](html-previews/customer-agizisha.html) |
| Customer | `/customer/express-air-cargo` | [customer-express-air-cargo.html](html-previews/customer-express-air-cargo.html) |
| Customer | `/customer/china-addresses` | [customer-china-addresses.html](html-previews/customer-china-addresses.html) |
| Sourcing Agent | `/agent/pending-approval` | [agent-pending-approval.html](html-previews/agent-pending-approval.html) |
| Sourcing Agent | `/agent/agizisha-orders` | [agent-agizisha-orders.html](html-previews/agent-agizisha-orders.html) |
| Sourcing Agent | `/agent/agizisha-storefront` | [agent-storefront.html](html-previews/agent-storefront.html) |
| Sourcing Agent | `/agent/batches` | [agent-batches.html](html-previews/agent-batches.html) |
| Sourcing Agent | `/agent/batches/:batchId/financials` | [agent-batch-financials.html](html-previews/agent-batch-financials.html) |
| Sourcing Agent | `/agent/orders/:orderId` | [agent-order-detail.html](html-previews/agent-order-detail.html) |
| Sourcing Agent | `/agent/batches/:batchId/packing-lists/new` | [agent-create-packing-list.html](html-previews/agent-create-packing-list.html) |
| Sourcing Agent | `/agent/packing-lists` | [agent-packing-lists.html](html-previews/agent-packing-lists.html) |
| Sourcing Agent | `/agent/packing-lists/:packingListId` | [agent-packing-list-detail.html](html-previews/agent-packing-list-detail.html) |
| Sourcing Agent | `/agent/express-air-cargo` | [agent-express-air-cargo.html](html-previews/agent-express-air-cargo.html) |
| Sourcing Agent | `/agent/financials` | [agent-financials.html](html-previews/agent-financials.html) |
| Sourcing Agent | `/agent/containers` | [agent-containers.html](html-previews/agent-containers.html) |
| Sourcing Agent | `/agent/containers/:containerId` | [agent-container-detail.html](html-previews/agent-container-detail.html) |
| Sourcing Agent | `/agent/reservations` | [agent-reservations.html](html-previews/agent-reservations.html) |
| Sourcing Agent | `/agent/track-shipments` | [agent-track-shipment.html](html-previews/agent-track-shipment.html) |
| Cargo Admin | `/cargo/warehouses` | [cargo-admin-warehouses.html](html-previews/cargo-admin-warehouses.html) |
| Cargo Admin | `/cargo/reservations` | [cargo-admin-reservations.html](html-previews/cargo-admin-reservations.html) |
| Cargo Admin | `/cargo/receipts` | [cargo-admin-receipts.html](html-previews/cargo-admin-receipts.html) |
| Cargo Admin | `/cargo/documentationworkspace` | [cargo-admin-documentation-workspace.html](html-previews/cargo-admin-documentation-workspace.html) |
| Cargo Admin | `/cargo/documentationworkspace/manual-cargo-intake` | [cargo-admin-manual-intake.html](html-previews/cargo-admin-manual-intake.html) |
| Cargo Admin | `/cargo/express-air-cargo` | [cargo-admin-express-air-cargo.html](html-previews/cargo-admin-express-air-cargo.html) |
| Super Admin | `/admin/sourcing-agents` | [super-admin-sourcing-agents.html](html-previews/super-admin-sourcing-agents.html) |
| Super Admin | `/admin/operators` | [super-admin-operators.html](html-previews/super-admin-operators.html) |
| Super Admin | `/admin/goods` | [super-admin-goods-classification.html](html-previews/super-admin-goods-classification.html) |
| Super Admin | `/admin/reservations` | [super-admin-reservations.html](html-previews/super-admin-reservations.html) |
| Super Admin | `/admin/commission` | [super-admin-commission.html](html-previews/super-admin-commission.html) |
| Super Admin | `/admin/track-shipments` | [super-admin-track-shipment.html](html-previews/super-admin-track-shipment.html) |

## Routes covered by the original or hand-authored preview set

| Role | Web route | HTML preview | Notes |
|---|---|---|---|
| Public | `/login` | [customer-login.html](html-previews/customer-login.html) | Registration and OTP states are also previewed by customer-register.html and customer-otp.html. |
| Customer | `/customer/dashboard` | [customer-dashboard.html](html-previews/customer-dashboard.html) |  |
| Customer | `/customer/containers` | [customer-search-container.html](html-previews/customer-search-container.html) | Container detail, reservation, and confirmation have supplementary previews. |
| Customer | `/customer/orders` | [customer-orders.html](html-previews/customer-orders.html) |  |
| Customer | `/customer/orders/:orderId` | [customer-order-details.html](html-previews/customer-order-details.html) |  |
| Customer | `/customer/track-shipments` | [customer-shipment-tracking.html](html-previews/customer-shipment-tracking.html) |  |
| Customer | `/customer/warehouse-access/:token` | [customer-warehouse-parcels.html](html-previews/customer-warehouse-parcels.html) | Collection-code state is previewed separately. |
| Sourcing Agent | `/agent/dashboard` | [agent-dashboard.html](html-previews/agent-dashboard.html) |  |
| Sourcing Agent | `/agent/batches/new` | [agent-create-batch.html](html-previews/agent-create-batch.html) |  |
| Sourcing Agent | `/agent/batches/:batchId` | [agent-batch-details.html](html-previews/agent-batch-details.html) | Product and order-generation actions have supplementary previews. |
| Cargo Admin | `/cargo/dashboard` | [cargo-admin-dashboard.html](html-previews/cargo-admin-dashboard.html) |  |
| Cargo Admin | `/cargo/containers` | [cargo-admin-container-management.html](html-previews/cargo-admin-container-management.html) |  |
| Cargo Admin | `/cargo/containers/new` | [cargo-admin-container-management.html](html-previews/cargo-admin-container-management.html) | This route opens the create state of the same container-management screen. |
| Cargo Admin | `/cargo/documentationworkspace/packing-lists` | [cargo-admin-packing-lists.html](html-previews/cargo-admin-packing-lists.html) | Legacy packing-list URLs redirect here. |
| Cargo Admin | `/cargo/documentationworkspace/customers` | [cargo-admin-customer-management.html](html-previews/cargo-admin-customer-management.html) | The legacy customer URL redirects here. |
| Cargo Admin | `/cargo/shipment-orders` | [cargo-admin-shipment-orders.html](html-previews/cargo-admin-shipment-orders.html) |  |
| Cargo Admin | `/cargo/fcl-requests` | [cargo-admin-fcl-requests.html](html-previews/cargo-admin-fcl-requests.html) |  |
| Cargo Admin | `/cargo/track-shipments` | [cargo-admin-track-shipment.html](html-previews/cargo-admin-track-shipment.html) |  |
| Cargo Admin | `/cargo/warehouse-automation` | [cargo-admin-warehouse-automation.html](html-previews/cargo-admin-warehouse-automation.html) |  |
| Super Admin | `/admin/dashboard` | [super-admin-dashboard.html](html-previews/super-admin-dashboard.html) |  |
| Super Admin | `/admin/users` | [super-admin-user-management.html](html-previews/super-admin-user-management.html) |  |
| Super Admin | `/admin/users/:userId` | [super-admin-user-details.html](html-previews/super-admin-user-details.html) |  |
| Super Admin | `/admin/pending-approvals` | [super-admin-approvals.html](html-previews/super-admin-approvals.html) |  |
| Super Admin | `/admin/audit-logs` | [super-admin-platform-activity.html](html-previews/super-admin-platform-activity.html) |  |
| Super Admin | `/admin/warehouse-automation` | [super-admin-warehouse-automation.html](html-previews/super-admin-warehouse-automation.html) |  |

Redirect-only routes reuse their destination preview: `/customer/batches*` → `/agizisha`; `/cargo/packing-lists` and `/cargo/customs-packing-lists` → the documentation packing-list view; `/cargo/customers` → the documentation customer view. The wildcard route returns to `/`.
