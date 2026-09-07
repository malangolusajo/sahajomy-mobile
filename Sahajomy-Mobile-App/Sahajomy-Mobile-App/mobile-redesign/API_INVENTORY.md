# Mobile API inventory

Full request signatures, declared response models, source lines and model fields are in `api-inventory.json`. Dependency expressions identify authentication/role guards; inline responses require handler inspection. Router composition must be reviewed when a source match is absent.

| Method | Route | Flutter source | Verification |
|---|---|---|---|
| POST | auth/send-otp | lib\features\auth\data\auth_repository.dart:39 | SOURCE MATCH (not live verified) |
| POST | auth/verify-otp | lib\features\auth\data\auth_repository.dart:54 | SOURCE MATCH (not live verified) |
| POST | auth/mfa/setup | lib\features\auth\data\auth_repository.dart:63 | SOURCE MATCH (not live verified) |
| POST | auth/mfa/verify | lib\features\auth\data\auth_repository.dart:82 | SOURCE MATCH (not live verified) |
| GET | auth/me | lib\features\auth\data\auth_repository.dart:91 | SOURCE MATCH (not live verified) |
| GET | auth/me | lib\features\auth\data\auth_repository.dart:111 | SOURCE MATCH (not live verified) |
| POST | auth/logout | lib\features\auth\data\auth_repository.dart:113 | SOURCE MATCH (not live verified) |
| GET | auth/me | lib\features\auth\data\auth_repository.dart:168 | SOURCE MATCH (not live verified) |
| POST | forwarding/prepare-address | lib\features\booking\data\guided_booking_repository.dart:28 | SOURCE MATCH (not live verified) |
| GET/POST (widget dependent) | cargo_admin/sea-bookings | lib\features\cargo_admin\presentation\cargo_admin_shell.dart:32 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET | cargo_admin/containers | lib\features\cargo_admin\containers\data\cargo_admin_containers_repository.dart:9 | SOURCE MATCH (not live verified) |
| GET | cargo_admin/dashboard | lib\features\cargo_admin\dashboard\data\cargo_admin_dashboard_repository.dart:9 | SOURCE MATCH (not live verified) |
| GET | cargo_admin/customs-packing-lists | lib\features\cargo_admin\documents\data\cargo_admin_documents_repository.dart:9 | SOURCE MATCH (not live verified) |
| GET | cargo_admin/financial/receipts | lib\features\cargo_admin\documents\data\cargo_admin_documents_repository.dart:12 | SOURCE MATCH (not live verified) |
| GET | cargo_admin/financial/invoices | lib\features\cargo_admin\documents\data\cargo_admin_documents_repository.dart:15 | SOURCE MATCH (not live verified) |
| GET | cargo_admin/customers | lib\features\cargo_admin\documents\data\cargo_admin_documents_repository.dart:18 | SOURCE MATCH (not live verified) |
| GET | cargo_admin/warehouse-automation/status | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:9 | SOURCE MATCH (not live verified) |
| POST | cargo_admin/warehouse-automation/warehouses/${Uri.encodeComponent(warehouseId)}/access-token | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:13 | SOURCE MATCH (not live verified) |
| DELETE | cargo_admin/warehouse-automation/warehouses/${Uri.encodeComponent(warehouseId)}/access-token | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:22 | SOURCE MATCH (not live verified) |
| POST | cargo_admin/warehouse-automation/intake/match | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:42 | SOURCE MATCH (not live verified) |
| POST | cargo_admin/warehouse-automation/intake/confirm | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:50 | SOURCE MATCH (not live verified) |
| PATCH | cargo_admin/warehouse-automation/intakes/${Uri.encodeComponent(intakeId)}/collection-readiness | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:61 | SOURCE MATCH (not live verified) |
| POST | cargo_admin/warehouse-automation/collection/verify | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:70 | SOURCE MATCH (not live verified) |
| POST | cargo_admin/warehouse-automation/collection/${Uri.encodeComponent(requestId)}/confirm | lib\features\cargo_admin\warehouse_automation\data\warehouse_automation_repository.dart:84 | SOURCE MATCH (not live verified) |
| GET | customer/express-air-cargo/bookings | lib\features\customer\air_cargo\data\customer_air_cargo_repository.dart:11 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/express-air-cargo/options | lib\features\customer\air_cargo\data\customer_air_cargo_repository.dart:14 | REQUIRES REVIEW (router composition or stale route) |
| POST | customer/express-air-cargo/book | lib\features\customer\air_cargo\data\customer_air_cargo_repository.dart:24 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/china-addresses | lib\features\customer\china_addresses\data\customer_china_addresses_repository.dart:9 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/containers | lib\features\customer\containers\data\customer_containers_repository.dart:9 | REQUIRES REVIEW (router composition or stale route) |
| GET | public/goods/categories | lib\features\customer\containers\data\customer_containers_repository.dart:12 | SOURCE MATCH (not live verified) |
| GET | customer/shipment-orders | lib\features\customer\dashboard\data\customer_dashboard_repository.dart:11 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/sea-bookings | lib\features\customer\dashboard\data\customer_dashboard_repository.dart:12 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/orders | lib\features\customer\dashboard\data\customer_dashboard_repository.dart:13 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/notifications | lib\features\customer\notifications\data\customer_notifications_repository.dart:9 | REQUIRES REVIEW (router composition or stale route) |
| PUT | customer/notifications/$notificationId/mark-read | lib\features\customer\notifications\data\customer_notifications_repository.dart:12 | REQUIRES REVIEW (router composition or stale route) |
| PUT | customer/notifications/mark-all-read | lib\features\customer\notifications\data\customer_notifications_repository.dart:15 | REQUIRES REVIEW (router composition or stale route) |
| DELETE | notifications/$notificationId | lib\features\customer\notifications\data\customer_notifications_repository.dart:18 | SOURCE MATCH (not live verified) |
| GET | customer/orders | lib\features\customer\orders\data\customer_orders_repository.dart:9 | REQUIRES REVIEW (router composition or stale route) |
| GET/POST (widget dependent) | customer/orders | lib\features\customer\orders\presentation\customer_order_list_page.dart:7 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET | customer/containers | lib\features\customer\reservations\data\customer_booking_repository.dart:9 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/sea-bookings | lib\features\customer\reservations\data\customer_booking_repository.dart:12 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/sea-bookings/$bookingId | lib\features\customer\reservations\data\customer_booking_repository.dart:15 | REQUIRES REVIEW (router composition or stale route) |
| POST | customer/sea-bookings | lib\features\customer\reservations\data\customer_booking_repository.dart:26 | REQUIRES REVIEW (router composition or stale route) |
| GET | customer/shipment-orders | lib\features\customer\shipments\data\customer_shipments_repository.dart:9 | REQUIRES REVIEW (router composition or stale route) |
| GET/POST (widget dependent) | customer/shipment-orders/ | lib\features\customer\shipments\presentation\shipment_list_page.dart:7 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET | tracking/customer/sea-bookings | lib\features\customer\tracking\data\customer_tracking_repository.dart:10 | SOURCE MATCH (not live verified) |
| GET | tracking/customer/bookings | lib\features\customer\tracking\data\customer_tracking_repository.dart:11 | SOURCE MATCH (not live verified) |
| GET | tracking/customer/shipment_orders | lib\features\customer\tracking\data\customer_tracking_repository.dart:12 | SOURCE MATCH (not live verified) |
| GET | customer/warehouse-access/${Uri.encodeComponent(opaqueToken)} | lib\features\customer\warehouse_access\data\customer_warehouse_access_repository.dart:11 | SOURCE MATCH (not live verified) |
| POST | customer/warehouse-access/${Uri.encodeComponent(opaqueToken)}/collection-requests | lib\features\customer\warehouse_access\data\customer_warehouse_access_repository.dart:32 | SOURCE MATCH (not live verified) |
| GET | public/containers | lib\features\public_services\data\public_services_repository.dart:9 | SOURCE MATCH (not live verified) |
| GET | public/agizisha/products | lib\features\public_services\data\public_services_repository.dart:12 | SOURCE MATCH (not live verified) |
| GET | public/agizisha/agents | lib\features\public_services\data\public_services_repository.dart:16 | SOURCE MATCH (not live verified) |
| GET | public/agizisha/products/${Uri.encodeComponent(productId)} | lib\features\public_services\data\public_services_repository.dart:23 | SOURCE MATCH (not live verified) |
| GET | public/batch/${Uri.encodeComponent(token)} | lib\features\public_services\data\public_services_repository.dart:31 | SOURCE MATCH (not live verified) |
| GET | public/receipt/verify/${Uri.encodeComponent(token)} | lib\features\public_services\data\public_services_repository.dart:39 | SOURCE MATCH (not live verified) |
| POST | fcl-quote-request | lib\features\public_services\data\public_services_repository.dart:46 | SOURCE MATCH (not live verified) |
| POST | public/agizisha/orders | lib\features\public_services\data\public_services_repository.dart:54 | SOURCE MATCH (not live verified) |
| POST | public/sourcing-agents/register | lib\features\public_services\data\public_services_repository.dart:62 | REQUIRES REVIEW (router composition or stale route) |
| GET/POST (widget dependent) | sourcing_agent/agizisha-orders | lib\features\reference\presentation\dedicated_preview_pages.dart:231 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/containers | lib\features\reference\presentation\dedicated_preview_pages.dart:272 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/express-air-cargo/bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:304 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/financials | lib\features\reference\presentation\dedicated_preview_pages.dart:315 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:376 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/public-profile | lib\features\reference\presentation\dedicated_preview_pages.dart:387 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | tracking/agent/shipment_orders | lib\features\reference\presentation\dedicated_preview_pages.dart:398 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/customers | lib\features\reference\presentation\dedicated_preview_pages.dart:416 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/express-air-cargo/bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:442 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/fcl-requests | lib\features\reference\presentation\dedicated_preview_pages.dart:453 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/notifications | lib\features\reference\presentation\dedicated_preview_pages.dart:471 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:496 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/shipment-orders | lib\features\reference\presentation\dedicated_preview_pages.dart:507 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | tracking/admin/shipment_orders | lib\features\reference\presentation\dedicated_preview_pages.dart:518 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/warehouses | lib\features\reference\presentation\dedicated_preview_pages.dart:537 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | customer/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:569 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | customer/orders | lib\features\reference\presentation\dedicated_preview_pages.dart:622 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/agizisha/agents | lib\features\reference\presentation\dedicated_preview_pages.dart:742 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/agizisha/products | lib\features\reference\presentation\dedicated_preview_pages.dart:753 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/agizisha/products | lib\features\reference\presentation\dedicated_preview_pages.dart:764 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/air-departure-schedules | lib\features\reference\presentation\dedicated_preview_pages.dart:775 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | fcl-quote-request | lib\features\reference\presentation\dedicated_preview_pages.dart:817 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/platform-stats | lib\features\reference\presentation\dedicated_preview_pages.dart:872 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/sourcing-agents/register | lib\features\reference\presentation\dedicated_preview_pages.dart:932 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/public/warehouses/search | lib\features\reference\presentation\dedicated_preview_pages.dart:985 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/public/warehouses/search | lib\features\reference\presentation\dedicated_preview_pages.dart:996 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | public/agizisha/products | lib\features\reference\presentation\dedicated_preview_pages.dart:1016 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/users/pending | lib\features\reference\presentation\dedicated_preview_pages.dart:1036 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/commission | lib\features\reference\presentation\dedicated_preview_pages.dart:1047 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/goods/categories | lib\features\reference\presentation\dedicated_preview_pages.dart:1073 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/notifications | lib\features\reference\presentation\dedicated_preview_pages.dart:1088 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/operators | lib\features\reference\presentation\dedicated_preview_pages.dart:1099 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:1117 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/sourcing-agents | lib\features\reference\presentation\dedicated_preview_pages.dart:1136 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | tracking/admin/shipment_orders | lib\features\reference\presentation\dedicated_preview_pages.dart:1147 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/china-addresses | lib\features\reference\presentation\dedicated_preview_pages.dart:1180 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:1191 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | subscriptions/current | lib\features\reference\presentation\dedicated_preview_pages.dart:1204 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo/finance/dashboard | lib\features\reference\presentation\dedicated_preview_pages.dart:1222 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | auth/me | lib\features\reference\presentation\dedicated_preview_pages.dart:1233 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | cargo_admin/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:1244 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | workspaces | lib\features\reference\presentation\dedicated_preview_pages.dart:1255 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | customer/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:1266 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | customer/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:1277 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/sea-bookings | lib\features\reference\presentation\dedicated_preview_pages.dart:1342 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/companies | lib\features\reference\presentation\dedicated_preview_pages.dart:1353 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/companies | lib\features\reference\presentation\dedicated_preview_pages.dart:1364 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/operators | lib\features\reference\presentation\dedicated_preview_pages.dart:1375 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | super_admin/subscriptions/overview | lib\features\reference\presentation\dedicated_preview_pages.dart:1386 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET/POST (widget dependent) | sourcing_agent/agizisha-orders | lib\features\sourcing_agent\presentation\sourcing_agent_shell.dart:32 | REQUIRES WIDGET/SCHEMA REVIEW |
| GET | sourcing_agent/batches | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:9 | SOURCE MATCH (not live verified) |
| GET | sourcing_agent/batches/$batchId | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:12 | SOURCE MATCH (not live verified) |
| GET | sourcing_agent/batches/$batchId/orders | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:15 | SOURCE MATCH (not live verified) |
| POST | sourcing_agent/batches | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:23 | SOURCE MATCH (not live verified) |
| POST | sourcing_agent/batches/$batchId/packing-lists | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:38 | SOURCE MATCH (not live verified) |
| POST | sourcing_agent/batches/$batchId/products | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:51 | SOURCE MATCH (not live verified) |
| GET | sourcing_agent/goods/categories | lib\features\sourcing_agent\batches\data\sourcing_agent_batches_repository.dart:65 | SOURCE MATCH (not live verified) |
| GET | super_admin/analytics/overview | lib\features\super_admin\dashboard\data\super_admin_dashboard_repository.dart:9 | SOURCE MATCH (not live verified) |
| GET | super_admin/users | lib\features\super_admin\users\data\super_admin_users_repository.dart:9 | SOURCE MATCH (not live verified) |
| PATCH | super_admin/users/${Uri.encodeComponent(userId)}/status | lib\features\super_admin\users\data\super_admin_users_repository.dart:24 | SOURCE MATCH (not live verified) |
| PATCH | super_admin/users/${Uri.encodeComponent(userId)}/verification | lib\features\super_admin\users\data\super_admin_users_repository.dart:36 | SOURCE MATCH (not live verified) |
| GET | super_admin/warehouse-automation/cargo-admins | lib\features\super_admin\warehouse_automation\data\super_admin_warehouse_automation_repository.dart:9 | SOURCE MATCH (not live verified) |
| PUT | super_admin/warehouse-automation/cargo-admins/$cargoAdminId | lib\features\super_admin\warehouse_automation\data\super_admin_warehouse_automation_repository.dart:14 | SOURCE MATCH (not live verified) |
