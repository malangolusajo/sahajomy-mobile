param(
  [string]$Workspace = (Get-Location).Path
)

$specPath = Join-Path $Workspace 'lib\features\reference\presentation\native_screen_specs.dart'
$outputPath = Join-Path $Workspace 'lib\features\reference\presentation\dedicated_preview_pages.dart'
$source = Get-Content -LiteralPath $specPath -Raw
$matches = [regex]::Matches($source, "fileName: '([^']+)'" )

$pageBuilders = @{
  'agent-add-product.html' = 'const SourcingAgentProductManagementPage()'
  'agent-batch-details.html' = 'const SourcingAgentBatchListPage()'
  'agent-batch-financials.html' = 'const SourcingAgentBatchListPage()'
  'customer-login.html' = 'const SignInPage()'
  'customer-otp.html' = 'const SignInPage()'
  'customer-register.html' = 'const SignInPage()'
  'customer-splash.html' = 'const WelcomePage()'
  'agent-batches.html' = 'const SourcingAgentBatchListPage()'
  'agent-create-batch.html' = 'const SourcingAgentCreateBatchPage()'
  'agent-create-packing-list.html' = 'const SourcingAgentBatchListPage()'
  'agent-dashboard.html' = 'const SourcingAgentDashboardPage()'
  'agent-generate-orders.html' = 'const SourcingAgentBatchListPage()'
  'agent-notifications.html' = 'const SourcingAgentNotificationsPage()'
  'agent-product-management.html' = 'const SourcingAgentProductManagementPage()'
  'agent-order-detail.html' = 'const SourcingAgentBatchListPage()'
  'agent-packing-list-detail.html' = 'const SourcingAgentBatchListPage()'
  'agent-packing-lists.html' = 'const SourcingAgentBatchListPage()'
  'agent-pending-approval.html' = 'const SourcingAgentDashboardPage()'
  'cargo-admin-container-management.html' = 'const CargoAdminContainerListPage()'
  'cargo-admin-dashboard.html' = 'const CargoAdminDashboardPage()'
  'cargo-admin-documentation-workspace.html' = 'const CargoAdminDocumentationWorkspacePage()'
  'cargo-admin-manual-intake.html' = 'const CargoAdminManualIntakePage()'
  'cargo-admin-packing-lists.html' = 'const CargoAdminPackingListsPage()'
  'cargo-admin-receipts.html' = 'const CargoAdminReceiptsPage()'
  'cargo-admin-warehouse-automation.html' = 'const CargoAdminWarehouseAutomationPage()'
  'customer-agizisha.html' = 'const CustomerOrderListPage()'
  'customer-china-addresses.html' = 'const ChinaAddressListPage()'
  'customer-booking-confirmation.html' = 'const ContainerListPage()'
  'customer-container-details.html' = 'const ContainerListPage()'
  'customer-containers.html' = 'const ContainerListPage()'
  'customer-dashboard.html' = 'const CustomerShell()'
  'customer-documents.html' = 'const CustomerDocumentsPage()'
  'customer-express-air-cargo.html' = 'const AirCargoBookingListPage()'
  'customer-notifications.html' = 'const CustomerNotificationsPage()'
  'customer-orders.html' = 'const CustomerOrderListPage()'
  'customer-packing-list.html' = 'const CustomerPackingListPage()'
  'customer-profile.html' = 'const CustomerProfilePage()'
  'customer-reservations.html' = 'const ReservationListPage()'
  'customer-reservation-detail.html' = 'const ReservationListPage()'
  'customer-reserve-cbm.html' = 'const ContainerListPage()'
  'customer-search-container.html' = 'const ContainerListPage()'
  'customer-shipment-order-detail.html' = 'const ShipmentListPage()'
  'customer-shipment-tracking.html' = 'const ShipmentTrackingPage()'
  'public-containers.html' = 'const PublicContainersPage()'
  'super-admin-dashboard.html' = 'const SuperAdminDashboardPage()'
  'super-admin-platform-activity.html' = 'const SuperAdminPlatformActivityPage()'
  'super-admin-user-management.html' = 'const SuperAdminUserListPage()'
  'super-admin-user-details.html' = 'const SuperAdminUserListPage()'
  'super-admin-warehouse-automation.html' = 'const SuperAdminWarehouseAutomationPage()'
}

$liveEndpoints = @{
  'agent-agizisha-orders.html' = 'sourcing_agent/agizisha-orders'
  'agent-containers.html' = 'sourcing_agent/containers'
  'agent-express-air-cargo.html' = 'sourcing_agent/express-air-cargo/bookings'
  'agent-financials.html' = 'sourcing_agent/financials'
  'agent-reservations.html' = 'sourcing_agent/reservations'
  'agent-storefront.html' = 'sourcing_agent/public-profile'
  'agent-track-shipment.html' = 'tracking/agent/shipment_orders'
  'cargo-admin-customer-management.html' = 'cargo_admin/customers'
  'cargo-admin-express-air-cargo.html' = 'cargo_admin/express-air-cargo/bookings'
  'cargo-admin-fcl-requests.html' = 'cargo_admin/fcl-requests'
  'cargo-admin-notifications.html' = 'cargo_admin/notifications'
  'cargo-admin-reservations.html' = 'cargo_admin/reservations'
  'cargo-admin-shipment-orders.html' = 'cargo_admin/shipment-orders'
  'cargo-admin-track-shipment.html' = 'tracking/admin/shipment_orders'
  'cargo-admin-warehouses.html' = 'cargo_admin/warehouses'
  'customer-collection-code.html' = 'customer/reservations'
  'customer-container-details.html' = 'customer/containers'
  'customer-order-details.html' = 'customer/orders'
  'customer-reservation-detail.html' = 'customer/reservations'
  'customer-shipment-order-detail.html' = 'customer/shipment-orders/'
  'public-agizisha-agent-storefront.html' = 'public/agizisha/agents'
  'public-agizisha-catalogue.html' = 'public/agizisha/products'
  'public-agizisha-product-detail.html' = 'public/agizisha/products'
  'public-air-cargo.html' = 'public/air-departure-schedules'
  'public-landing.html' = 'public/platform-stats'
  'public-warehouse-detail.html' = 'cargo_admin/public/warehouses/search'
  'public-warehouses.html' = 'cargo_admin/public/warehouses/search'
  'shared-product-detail.html' = 'public/agizisha/products'
  'super-admin-approvals.html' = 'super_admin/users/pending'
  'super-admin-commission.html' = 'super_admin/commission'
  'super-admin-goods-classification.html' = 'super_admin/goods/categories'
  'super-admin-notifications.html' = 'super_admin/notifications'
  'super-admin-operators.html' = 'super_admin/operators'
  'super-admin-reservations.html' = 'super_admin/reservations'
  'super-admin-sourcing-agents.html' = 'super_admin/sourcing-agents'
  'super-admin-track-shipment.html' = 'tracking/admin/shipment_orders'
  'super-admin-user-details.html' = 'super_admin/users/recent'
}

$formBuilders = @{
  'public-fcl-quote-request.html' = @(
    "role: 'Public',", "title: 'Request an FCL quote',", "endpoint: 'fcl-quote-request',", "fields: [", "ApiFormField(name: 'product', label: 'Product', required: true),", "ApiFormField(name: 'specifications', label: 'Specifications', required: true, multiline: true),", "ApiFormField(name: 'supplier_status', label: 'Supplier status', required: true),", "ApiFormField(name: 'incoterm', label: 'Incoterm', required: true),", "ApiFormField(name: 'destination', label: 'Destination', required: true),", "ApiFormField(name: 'company_name', label: 'Company name', required: true),", "ApiFormField(name: 'business_license', label: 'Business license', required: true),", "ApiFormField(name: 'email', label: 'Email', required: true),", "ApiFormField(name: 'whatsapp_number', label: 'WhatsApp number', required: true),", "]"
  )
  'public-sourcing-agent-registration.html' = @(
    "role: 'Public',", "title: 'Become a sourcing agent',", "endpoint: 'public/sourcing-agents/register',", "multipart: true,", "fields: [", "ApiFormField(name: 'full_name', label: 'Full name', required: true),", "ApiFormField(name: 'phone', label: 'Phone', required: true),", "ApiFormField(name: 'email', label: 'Email', required: true),", "ApiFormField(name: 'whatsapp', label: 'WhatsApp'),", "ApiFormField(name: 'instagram', label: 'Instagram'),", "ApiFormField(name: 'tiktok', label: 'TikTok'),", "ApiFormField(name: 'niche', label: 'Sourcing niche', required: true),", "ApiFormField(name: 'location', label: 'Location', required: true),", "ApiFormField(name: 'bio', label: 'About you', multiline: true),", "ApiFormField(name: 'years_experience', label: 'Years of experience', numeric: true),", "]"
  )
  'super-admin-commission.html' = @(
    "role: 'Super Admin',", "title: 'Commission settings',", "endpoint: 'super_admin/commission',", "fields: [ApiFormField(name: 'commission_percentage', label: 'Commission percentage', required: true, numeric: true)]"
  )
  'super-admin-goods-classification.html' = @(
    "role: 'Super Admin',", "title: 'Create goods category',", "endpoint: 'super_admin/goods/categories',", "fields: [ApiFormField(name: 'name', label: 'Category name', required: true), ApiFormField(name: 'description', label: 'Description', multiline: true)]"
  )
}

function Get-PageClassName([string]$fileName) {
  $name = $fileName.Replace('.html', '')
  $parts = $name -split '-'
  $pascal = ($parts | ForEach-Object { $_.Substring(0, 1).ToUpperInvariant() + $_.Substring(1) }) -join ''
  return "${pascal}PreviewPage"
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("// GENERATED CODE - DO NOT MODIFY BY HAND.")
$lines.Add("// Regenerate with: .\tool\generate_dedicated_preview_pages.ps1")
$lines.Add("")
$lines.Add("import 'package:flutter/material.dart';")
$lines.Add("")
$lines.Add("import 'native_reference_screen.dart';")
$lines.Add("import 'native_screen_specs.dart';")
$lines.Add("import '../../public_services/presentation/public_containers_page.dart';")
$lines.Add("import 'live_workflow_page.dart';")
$lines.Add("import 'api_form_page.dart';")
$lines.Add("import '../../auth/presentation/sign_in_page.dart';")
$lines.Add("import '../../auth/presentation/welcome_page.dart';")
$lines.Add("import '../../sourcing_agent/batches/presentation/sourcing_agent_batch_list_page.dart';")
$lines.Add("import '../../sourcing_agent/batches/presentation/sourcing_agent_batch_workflow_pages.dart';")
$lines.Add("import '../../sourcing_agent/dashboard/presentation/sourcing_agent_dashboard_page.dart';")
$lines.Add("import '../../sourcing_agent/notifications/presentation/sourcing_agent_notifications_page.dart';")
$lines.Add("import '../../sourcing_agent/products/presentation/sourcing_agent_product_management_page.dart';")
$lines.Add("import '../../cargo_admin/containers/presentation/cargo_admin_container_list_page.dart';")
$lines.Add("import '../../cargo_admin/dashboard/presentation/cargo_admin_dashboard_page.dart';")
$lines.Add("import '../../cargo_admin/documents/presentation/cargo_admin_documentation_workspace_page.dart';")
$lines.Add("import '../../cargo_admin/warehouse_automation/presentation/cargo_admin_warehouse_automation_page.dart';")
$lines.Add("import '../../customer/air_cargo/presentation/air_cargo_booking_list_page.dart';")
$lines.Add("import '../../customer/china_addresses/presentation/china_address_list_page.dart';")
$lines.Add("import '../../customer/containers/presentation/container_list_page.dart';")
$lines.Add("import '../../customer/dashboard/presentation/customer_shell.dart';")
$lines.Add("import '../../customer/documents/presentation/customer_documents_page.dart';")
$lines.Add("import '../../customer/notifications/presentation/customer_notifications_page.dart';")
$lines.Add("import '../../customer/orders/presentation/customer_order_list_page.dart';")
$lines.Add("import '../../customer/packing_lists/presentation/customer_packing_list_page.dart';")
$lines.Add("import '../../customer/profile/presentation/customer_profile_page.dart';")
$lines.Add("import '../../customer/reservations/presentation/reservation_list_page.dart';")
$lines.Add("import '../../customer/shipments/presentation/shipment_list_page.dart';")
$lines.Add("import '../../customer/tracking/presentation/shipment_tracking_page.dart';")
$lines.Add("import '../../super_admin/activity/presentation/super_admin_platform_activity_page.dart';")
$lines.Add("import '../../super_admin/dashboard/presentation/super_admin_dashboard_page.dart';")
$lines.Add("import '../../super_admin/users/presentation/super_admin_user_list_page.dart';")
$lines.Add("import '../../super_admin/warehouse_automation/presentation/super_admin_warehouse_automation_page.dart';")
$lines.Add("")
$lines.Add("Widget dedicatedPreviewPageFor(NativeScreenSpec spec) => switch (spec.fileName) {")
foreach ($match in $matches) {
  $fileName = $match.Groups[1].Value
  $className = Get-PageClassName $fileName
  $lines.Add("  '$fileName' => const $className(),")
}
$lines.Add("  _ => throw ArgumentError.value(spec.fileName, 'spec.fileName', 'Unknown preview'),")
$lines.Add("};")
$lines.Add("")
foreach ($match in $matches) {
  $fileName = $match.Groups[1].Value
  $className = Get-PageClassName $fileName
  $lines.Add("class $className extends StatelessWidget {")
  $lines.Add("  const $className({super.key});")
  $lines.Add("")
  $lines.Add("  @override")
  if ($formBuilders.ContainsKey($fileName)) {
    $lines.Add("  Widget build(BuildContext context) => ApiFormPage(")
    foreach ($line in $formBuilders[$fileName]) { $lines.Add("    $line") }
    $lines.Add("  );")
  } elseif ($pageBuilders.ContainsKey($fileName)) {
    $lines.Add("  Widget build(BuildContext context) => $($pageBuilders[$fileName]);")
  } elseif ($liveEndpoints.ContainsKey($fileName)) {
    $lines.Add("  Widget build(BuildContext context) => LiveWorkflowPage(")
    $lines.Add("    role: nativeScreenSpecFor('$fileName').role,")
    $lines.Add("    title: nativeScreenSpecFor('$fileName').title,")
    $lines.Add("    endpoint: '$($liveEndpoints[$fileName])',")
    $lines.Add("  );")
  } else {
    $lines.Add("  Widget build(BuildContext context) => PreviewPageLayout(")
    $lines.Add("    spec: nativeScreenSpecFor('$fileName'),")
    $lines.Add("  );")
  }
  $lines.Add("}")
  $lines.Add("")
}

Set-Content -LiteralPath $outputPath -Value $lines -Encoding utf8
