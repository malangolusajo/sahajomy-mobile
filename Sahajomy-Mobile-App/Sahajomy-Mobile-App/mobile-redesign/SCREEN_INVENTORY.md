# Mobile screen inventory

Source-based inventory. Source matching is not live API verification. No screen is classified fully functional before request, response, state and permission checks.

| Screen | Role | Classification | Routes / source |
|---|---|---|---|
| Add a batch product | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Agizisha orders | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/agizisha-orders |
| August electronics batch | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/batches/:batchId |
| Batch financials | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/batches/:batchId/financials |
| Sourcing batches | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/batches |
| Container details | Sourcing Agent | D — PLACEHOLDER / FUTURE | /agent/containers/:containerId |
| Book container space | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/containers |
| Open a sourcing batch | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/batches/new |
| Create packing list | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/batches/:batchId/packing-lists/new |
| Your sourcing desk | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/dashboard |
| Express Air Cargo | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/express-air-cargo |
| Financials | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/financials |
| Generate customer orders | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Batch activity | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Order details | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/orders/:orderId |
| Packing list details | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/packing-lists/:packingListId |
| Packing lists | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/packing-lists |
| Approval pending | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/pending-approval |
| Product management | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| My bookings | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Public storefront | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/agizisha-storefront |
| Track shipments | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/track-shipments |
| Container management | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/containers/new, /cargo/containers |
| Customer management | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Today’s operations | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/dashboard |
| Cargo documentation | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/documentationworkspace |
| Express Air Cargo | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/express-air-cargo |
| Full-container requests | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/fcl-requests |
| Manual cargo intake | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Operational alerts | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Consolidated packing lists | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Receipts and invoices | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/receipts |
| Bookings | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Shipment orders | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/shipment-orders |
| Track a shipment | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/track-shipments |
| Warehouse automation | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Manage warehouses | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/warehouses |
| Agizisha | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/agizisha |
| Space booked | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| My China addresses | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/china-addresses |
| Collection code | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Dar es Salaam bound | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Good morning, Amina | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/dashboard |
| Shipping documents | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/documents |
| Express Air Cargo | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/express-air-cargo |
| Welcome back | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /login |
| Updates for you | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/notifications |
| Order #SO-10482 | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/orders/:orderId |
| Your orders | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/orders |
| Enter verification code | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Container packing list | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Amina Mussa | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/profile |
| Start shipping with confidence | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Booking details | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| My bookings | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/reservations |
| Book your CBM | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Find container space | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/containers |
| Shipment order | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Shipment progress | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/track-shipments, /customer/track-shipment |
| Welcome to easier shipping | Customer | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| My warehouse parcels | Customer | D — PLACEHOLDER / FUTURE | /customer/warehouse-access/:token |
| About Sahajomy | Public | C — PRESENTATIONAL | /about |
| Accessibility | Public | D — PLACEHOLDER / FUTURE | /accessibility |
| Agent storefront | Public | B — PARTIALLY FUNCTIONAL / verification pending | /agizisha/agents/:handle |
| Agizisha marketplace | Public | B — PARTIALLY FUNCTIONAL / verification pending | /agizisha |
| Product details | Public | B — PARTIALLY FUNCTIONAL / verification pending | /agizisha/product/:id |
| Express Air Cargo | Public | B — PARTIALLY FUNCTIONAL / verification pending | /air-cargo |
| Contact Sahajomy | Public | C — PRESENTATIONAL | /contact |
| Available containers | Public | B — PARTIALLY FUNCTIONAL / verification pending | /public/containers |
| Cookie information | Public | D — PLACEHOLDER / FUTURE | /cookies |
| Frequently asked questions | Public | C — PRESENTATIONAL | /faq |
| Request an FCL quote | Public | B — PARTIALLY FUNCTIONAL / verification pending | /fcl-quote-request |
| Share feedback | Public | D — PLACEHOLDER / FUTURE | /feedback |
| How it works | Public | C — PRESENTATIONAL | /how-it-works |
| Source, ship, and track | Public | B — PARTIALLY FUNCTIONAL / verification pending | / |
| Legal information | Public | D — PLACEHOLDER / FUTURE | /legal |
| Pricing | Public | C — PRESENTATIONAL | /pricing |
| Privacy policy | Public | C — PRESENTATIONAL | /privacy |
| Verify a receipt | Public | D — PLACEHOLDER / FUTURE | /verify-receipt |
| Shared sourcing batch | Public | D — PLACEHOLDER / FUTURE | /shared/:token |
| Sitemap | Public | D — PLACEHOLDER / FUTURE | /sitemap |
| Become a sourcing agent | Public | B — PARTIALLY FUNCTIONAL / verification pending | /sourcing-agent/register |
| Support tickets | Public | D — PLACEHOLDER / FUTURE | /support/tickets |
| Support centre | Public | D — PLACEHOLDER / FUTURE | /support |
| Terms of service | Public | C — PRESENTATIONAL | /terms |
| Warehouse details | Public | B — PARTIALLY FUNCTIONAL / verification pending | /warehouses/:warehouseSlug |
| Warehouses | Public | B — PARTIALLY FUNCTIONAL / verification pending | /warehouses |
| Air shipping label | Shared | D — PLACEHOLDER / FUTURE | /label/air/:bookingId |
| Sourcing product | Shared | B — PARTIALLY FUNCTIONAL / verification pending | /product/:productId |
| Sea shipping label | Shared | D — PLACEHOLDER / FUTURE | /label/sea/:seaBookingId |
| Pending approvals | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/pending-approvals |
| Commission settings | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/commission |
| Platform overview | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/dashboard |
| Goods classification | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/goods |
| Governance alerts | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Operators | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/operators |
| Platform activity | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/audit-logs |
| Platform bookings | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/reservations |
| Platform settings | Super Admin | D — PLACEHOLDER / FUTURE | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Sourcing agents | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/sourcing-agents |
| Track shipments | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/track-shipments |
| Amina Mussa | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/users/:userId |
| User management | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/users |
| Automation entitlements | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| My China addresses | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/china-addresses |
| My sea bookings | Sourcing Agent | B — PARTIALLY FUNCTIONAL / verification pending | /agent/sea-bookings |
| Billing and usage | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/settings/billing |
| Customers and contacts | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | lib/features/reference/presentation/dedicated_preview_pages.dart |
| Financial analytics | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/finance |
| Approval pending | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/pending-approval |
| Sea bookings | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/sea-bookings |
| Staff and branches | Cargo Admin | B — PARTIALLY FUNCTIONAL / verification pending | /cargo/settings/staff-branches |
| Sea booking details | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/sea-bookings/:seaBookingId |
| My sea bookings | Customer | B — PARTIALLY FUNCTIONAL / verification pending | /customer/sea-bookings |
| Air cargo across Africa | Public | C — PRESENTATIONAL | /air-cargo-africa |
| Register a cargo company | Public | D — PLACEHOLDER / FUTURE | /cargo-operator/register |
| China sourcing for Africa | Public | C — PRESENTATIONAL | /china-sourcing-africa |
| Sea freight across Africa | Public | C — PRESENTATIONAL | /sea-freight-africa |
| Cargo company invitation | Public | D — PLACEHOLDER / FUTURE | /staff-invitation |
| Switch workspace | Shared | B — PARTIALLY FUNCTIONAL / verification pending | /account/workspaces |
| Platform bookings | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/bookings |
| Cargo companies | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/companies |
| Cargo company details | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/companies/:companyId |
| Cargo administrator | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/operators/:operatorId |
| Subscriptions and costs | Super Admin | B — PARTIALLY FUNCTIONAL / verification pending | /admin/subscriptions |
| MfaPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\auth\presentation\mfa_page.dart |
| OtpPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\auth\presentation\otp_page.dart |
| RegistrationPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\auth\presentation\registration_page.dart |
| SignInPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\auth\presentation\sign_in_page.dart |
| WelcomePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\auth\presentation\welcome_page.dart |
| GuidedSeaBookingPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\booking\presentation\sea_booking_flow.dart |
| CargoAdminShell | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\presentation\cargo_admin_shell.dart |
| _CargoAdminMorePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\presentation\cargo_admin_shell.dart |
| CargoAdminContainerListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\containers\presentation\cargo_admin_container_list_page.dart |
| CargoAdminDashboardPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\dashboard\presentation\cargo_admin_dashboard_page.dart |
| CargoAdminDocumentationWorkspacePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\documents\presentation\cargo_admin_documentation_workspace_page.dart |
| CargoAdminPackingListsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\documents\presentation\cargo_admin_documentation_workspace_page.dart |
| CargoAdminReceiptsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\documents\presentation\cargo_admin_documentation_workspace_page.dart |
| CargoAdminCustomerRecordsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\documents\presentation\cargo_admin_documentation_workspace_page.dart |
| CargoAdminManualIntakePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\documents\presentation\cargo_admin_documentation_workspace_page.dart |
| CargoAdminWarehouseAutomationPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\warehouse_automation\presentation\cargo_admin_warehouse_automation_page.dart |
| _BarcodeScannerPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\cargo_admin\warehouse_automation\presentation\cargo_admin_warehouse_automation_page.dart |
| AirCargoBookingListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\air_cargo\presentation\air_cargo_booking_list_page.dart |
| CreateAirCargoBookingPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\air_cargo\presentation\create_air_cargo_booking_page.dart |
| ChinaAddressListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\china_addresses\presentation\china_address_list_page.dart |
| ContainerDetailPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\containers\presentation\container_detail_page.dart |
| ContainerListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\containers\presentation\container_list_page.dart |
| CustomerShell | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\dashboard\presentation\customer_shell.dart |
| CustomerHomePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\dashboard\presentation\customer_shell.dart |
| CustomerDocumentsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\documents\presentation\customer_documents_page.dart |
| CustomerMorePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\more\presentation\customer_more_page.dart |
| CustomerNotificationsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\notifications\presentation\customer_notifications_page.dart |
| CustomerOrderListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\orders\presentation\customer_order_list_page.dart |
| CustomerPackingListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\packing_lists\presentation\customer_packing_list_page.dart |
| CustomerProfilePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\profile\presentation\customer_profile_page.dart |
| BookingConfirmationPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\reservations\presentation\booking_confirmation_page.dart |
| BookingDetailPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\reservations\presentation\booking_detail_page.dart |
| BookingListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\reservations\presentation\booking_list_page.dart |
| BookContainerPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\reservations\presentation\book_container_page.dart |
| ShipmentListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\shipments\presentation\shipment_list_page.dart |
| ShipmentTrackingPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\tracking\presentation\shipment_tracking_page.dart |
| CollectionCodePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\warehouse_access\presentation\collection_code_page.dart |
| CustomerWarehouseParcelsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\customer\warehouse_access\presentation\customer_warehouse_parcels_page.dart |
| OnboardingPage | Native | C — LOCKED | lib\features\onboarding\presentation\onboarding_page.dart |
| SplashPage | Native | C — LOCKED | lib\features\onboarding\presentation\splash_page.dart |
| OfficialInformationPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\public_services\presentation\official_information_page.dart |
| PublicContainersPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\public_services\presentation\public_containers_page.dart |
| SourcingAgentShell | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\presentation\sourcing_agent_shell.dart |
| _SourcingAgentMorePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\presentation\sourcing_agent_shell.dart |
| SourcingAgentBatchDetailPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_detail_page.dart |
| SourcingAgentBatchListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_list_page.dart |
| SourcingAgentCreateBatchPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentAddProductPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentGenerateOrdersPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentBatchFinancialsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentPackingListCreatePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentPackingListListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentPackingListDetailPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentOrderDetailPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\batches\presentation\sourcing_agent_batch_workflow_pages.dart |
| SourcingAgentDashboardPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\dashboard\presentation\sourcing_agent_dashboard_page.dart |
| SourcingAgentNotificationsPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\notifications\presentation\sourcing_agent_notifications_page.dart |
| SourcingAgentProductManagementPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\sourcing_agent\products\presentation\sourcing_agent_product_management_page.dart |
| SuperAdminShell | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\super_admin\presentation\super_admin_shell.dart |
| _SuperAdminMorePage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\super_admin\presentation\super_admin_shell.dart |
| SuperAdminPlatformActivityPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\super_admin\activity\presentation\super_admin_platform_activity_page.dart |
| SuperAdminDashboardPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\super_admin\dashboard\presentation\super_admin_dashboard_page.dart |
| SuperAdminUserListPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\super_admin\users\presentation\super_admin_user_list_page.dart |
| SuperAdminWarehouseAutomationPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\super_admin\warehouse_automation\presentation\super_admin_warehouse_automation_page.dart |
| WorkspaceSelectionPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\features\workspaces\presentation\workspace_selection_page.dart |
| FeatureMenuPage | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\shared\presentation\feature_menu_page.dart |
| RoleShell | Native | B — PARTIALLY FUNCTIONAL / verification pending | lib\shared\presentation\role_shell.dart |
