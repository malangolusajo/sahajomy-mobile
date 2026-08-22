// GENERATED CODE - DO NOT MODIFY BY HAND.
// Regenerate with: .\tool\generate_dedicated_preview_pages.ps1

import 'package:flutter/material.dart';

import 'native_reference_screen.dart';
import 'native_screen_specs.dart';
import '../../public_services/presentation/public_containers_page.dart';
import 'live_workflow_page.dart';
import 'api_form_page.dart';
import '../../auth/presentation/sign_in_page.dart';
import '../../auth/presentation/welcome_page.dart';
import '../../sourcing_agent/batches/presentation/sourcing_agent_batch_list_page.dart';
import '../../sourcing_agent/batches/presentation/sourcing_agent_batch_workflow_pages.dart';
import '../../sourcing_agent/dashboard/presentation/sourcing_agent_dashboard_page.dart';
import '../../sourcing_agent/notifications/presentation/sourcing_agent_notifications_page.dart';
import '../../sourcing_agent/products/presentation/sourcing_agent_product_management_page.dart';
import '../../cargo_admin/containers/presentation/cargo_admin_container_list_page.dart';
import '../../cargo_admin/dashboard/presentation/cargo_admin_dashboard_page.dart';
import '../../cargo_admin/documents/presentation/cargo_admin_documentation_workspace_page.dart';
import '../../cargo_admin/warehouse_automation/presentation/cargo_admin_warehouse_automation_page.dart';
import '../../customer/air_cargo/presentation/air_cargo_booking_list_page.dart';
import '../../customer/china_addresses/presentation/china_address_list_page.dart';
import '../../customer/containers/presentation/container_list_page.dart';
import '../../customer/dashboard/presentation/customer_shell.dart';
import '../../customer/documents/presentation/customer_documents_page.dart';
import '../../customer/notifications/presentation/customer_notifications_page.dart';
import '../../customer/orders/presentation/customer_order_list_page.dart';
import '../../customer/packing_lists/presentation/customer_packing_list_page.dart';
import '../../customer/profile/presentation/customer_profile_page.dart';
import '../../customer/reservations/presentation/reservation_list_page.dart';
import '../../customer/shipments/presentation/shipment_list_page.dart';
import '../../customer/tracking/presentation/shipment_tracking_page.dart';
import '../../super_admin/activity/presentation/super_admin_platform_activity_page.dart';
import '../../super_admin/dashboard/presentation/super_admin_dashboard_page.dart';
import '../../super_admin/users/presentation/super_admin_user_list_page.dart';
import '../../super_admin/warehouse_automation/presentation/super_admin_warehouse_automation_page.dart';

Widget dedicatedPreviewPageFor(
  NativeScreenSpec spec,
) => switch (spec.fileName) {
  'agent-add-product.html' => const AgentAddProductPreviewPage(),
  'agent-agizisha-orders.html' => const AgentAgizishaOrdersPreviewPage(),
  'agent-batch-details.html' => const AgentBatchDetailsPreviewPage(),
  'agent-batch-financials.html' => const AgentBatchFinancialsPreviewPage(),
  'agent-batches.html' => const AgentBatchesPreviewPage(),
  'agent-container-detail.html' => const AgentContainerDetailPreviewPage(),
  'agent-containers.html' => const AgentContainersPreviewPage(),
  'agent-create-batch.html' => const AgentCreateBatchPreviewPage(),
  'agent-create-packing-list.html' => const AgentCreatePackingListPreviewPage(),
  'agent-dashboard.html' => const AgentDashboardPreviewPage(),
  'agent-express-air-cargo.html' => const AgentExpressAirCargoPreviewPage(),
  'agent-financials.html' => const AgentFinancialsPreviewPage(),
  'agent-generate-orders.html' => const AgentGenerateOrdersPreviewPage(),
  'agent-notifications.html' => const AgentNotificationsPreviewPage(),
  'agent-order-detail.html' => const AgentOrderDetailPreviewPage(),
  'agent-packing-list-detail.html' => const AgentPackingListDetailPreviewPage(),
  'agent-packing-lists.html' => const AgentPackingListsPreviewPage(),
  'agent-pending-approval.html' => const AgentPendingApprovalPreviewPage(),
  'agent-product-management.html' => const AgentProductManagementPreviewPage(),
  'agent-reservations.html' => const AgentReservationsPreviewPage(),
  'agent-storefront.html' => const AgentStorefrontPreviewPage(),
  'agent-track-shipment.html' => const AgentTrackShipmentPreviewPage(),
  'cargo-admin-container-management.html' =>
    const CargoAdminContainerManagementPreviewPage(),
  'cargo-admin-customer-management.html' =>
    const CargoAdminCustomerManagementPreviewPage(),
  'cargo-admin-dashboard.html' => const CargoAdminDashboardPreviewPage(),
  'cargo-admin-documentation-workspace.html' =>
    const CargoAdminDocumentationWorkspacePreviewPage(),
  'cargo-admin-express-air-cargo.html' =>
    const CargoAdminExpressAirCargoPreviewPage(),
  'cargo-admin-fcl-requests.html' => const CargoAdminFclRequestsPreviewPage(),
  'cargo-admin-manual-intake.html' => const CargoAdminManualIntakePreviewPage(),
  'cargo-admin-notifications.html' =>
    const CargoAdminNotificationsPreviewPage(),
  'cargo-admin-packing-lists.html' => const CargoAdminPackingListsPreviewPage(),
  'cargo-admin-receipts.html' => const CargoAdminReceiptsPreviewPage(),
  'cargo-admin-reservations.html' => const CargoAdminReservationsPreviewPage(),
  'cargo-admin-shipment-orders.html' =>
    const CargoAdminShipmentOrdersPreviewPage(),
  'cargo-admin-track-shipment.html' =>
    const CargoAdminTrackShipmentPreviewPage(),
  'cargo-admin-warehouse-automation.html' =>
    const CargoAdminWarehouseAutomationPreviewPage(),
  'cargo-admin-warehouses.html' => const CargoAdminWarehousesPreviewPage(),
  'customer-agizisha.html' => const CustomerAgizishaPreviewPage(),
  'customer-booking-confirmation.html' =>
    const CustomerBookingConfirmationPreviewPage(),
  'customer-china-addresses.html' => const CustomerChinaAddressesPreviewPage(),
  'customer-collection-code.html' => const CustomerCollectionCodePreviewPage(),
  'customer-container-details.html' =>
    const CustomerContainerDetailsPreviewPage(),
  'customer-dashboard.html' => const CustomerDashboardPreviewPage(),
  'customer-documents.html' => const CustomerDocumentsPreviewPage(),
  'customer-express-air-cargo.html' =>
    const CustomerExpressAirCargoPreviewPage(),
  'customer-login.html' => const CustomerLoginPreviewPage(),
  'customer-notifications.html' => const CustomerNotificationsPreviewPage(),
  'customer-order-details.html' => const CustomerOrderDetailsPreviewPage(),
  'customer-orders.html' => const CustomerOrdersPreviewPage(),
  'customer-otp.html' => const CustomerOtpPreviewPage(),
  'customer-packing-list.html' => const CustomerPackingListPreviewPage(),
  'customer-profile.html' => const CustomerProfilePreviewPage(),
  'customer-register.html' => const CustomerRegisterPreviewPage(),
  'customer-reservation-detail.html' =>
    const CustomerReservationDetailPreviewPage(),
  'customer-reservations.html' => const CustomerReservationsPreviewPage(),
  'customer-reserve-cbm.html' => const CustomerReserveCbmPreviewPage(),
  'customer-search-container.html' =>
    const CustomerSearchContainerPreviewPage(),
  'customer-shipment-order-detail.html' =>
    const CustomerShipmentOrderDetailPreviewPage(),
  'customer-shipment-tracking.html' =>
    const CustomerShipmentTrackingPreviewPage(),
  'customer-splash.html' => const CustomerSplashPreviewPage(),
  'customer-warehouse-parcels.html' =>
    const CustomerWarehouseParcelsPreviewPage(),
  'public-about.html' => const PublicAboutPreviewPage(),
  'public-accessibility.html' => const PublicAccessibilityPreviewPage(),
  'public-agizisha-agent-storefront.html' =>
    const PublicAgizishaAgentStorefrontPreviewPage(),
  'public-agizisha-catalogue.html' =>
    const PublicAgizishaCataloguePreviewPage(),
  'public-agizisha-product-detail.html' =>
    const PublicAgizishaProductDetailPreviewPage(),
  'public-air-cargo.html' => const PublicAirCargoPreviewPage(),
  'public-contact.html' => const PublicContactPreviewPage(),
  'public-containers.html' => const PublicContainersPreviewPage(),
  'public-cookies.html' => const PublicCookiesPreviewPage(),
  'public-faq.html' => const PublicFaqPreviewPage(),
  'public-fcl-quote-request.html' => const PublicFclQuoteRequestPreviewPage(),
  'public-feedback.html' => const PublicFeedbackPreviewPage(),
  'public-how-it-works.html' => const PublicHowItWorksPreviewPage(),
  'public-landing.html' => const PublicLandingPreviewPage(),
  'public-legal.html' => const PublicLegalPreviewPage(),
  'public-pricing.html' => const PublicPricingPreviewPage(),
  'public-privacy.html' => const PublicPrivacyPreviewPage(),
  'public-receipt-verification.html' =>
    const PublicReceiptVerificationPreviewPage(),
  'public-shared-batch.html' => const PublicSharedBatchPreviewPage(),
  'public-sitemap.html' => const PublicSitemapPreviewPage(),
  'public-sourcing-agent-registration.html' =>
    const PublicSourcingAgentRegistrationPreviewPage(),
  'public-support-tickets.html' => const PublicSupportTicketsPreviewPage(),
  'public-support.html' => const PublicSupportPreviewPage(),
  'public-terms.html' => const PublicTermsPreviewPage(),
  'public-warehouse-detail.html' => const PublicWarehouseDetailPreviewPage(),
  'public-warehouses.html' => const PublicWarehousesPreviewPage(),
  'shared-air-shipping-label.html' => const SharedAirShippingLabelPreviewPage(),
  'shared-product-detail.html' => const SharedProductDetailPreviewPage(),
  'shared-sea-shipping-label.html' => const SharedSeaShippingLabelPreviewPage(),
  'super-admin-approvals.html' => const SuperAdminApprovalsPreviewPage(),
  'super-admin-commission.html' => const SuperAdminCommissionPreviewPage(),
  'super-admin-dashboard.html' => const SuperAdminDashboardPreviewPage(),
  'super-admin-goods-classification.html' =>
    const SuperAdminGoodsClassificationPreviewPage(),
  'super-admin-notifications.html' =>
    const SuperAdminNotificationsPreviewPage(),
  'super-admin-operators.html' => const SuperAdminOperatorsPreviewPage(),
  'super-admin-platform-activity.html' =>
    const SuperAdminPlatformActivityPreviewPage(),
  'super-admin-reservations.html' => const SuperAdminReservationsPreviewPage(),
  'super-admin-settings.html' => const SuperAdminSettingsPreviewPage(),
  'super-admin-sourcing-agents.html' =>
    const SuperAdminSourcingAgentsPreviewPage(),
  'super-admin-track-shipment.html' =>
    const SuperAdminTrackShipmentPreviewPage(),
  'super-admin-user-details.html' => const SuperAdminUserDetailsPreviewPage(),
  'super-admin-user-management.html' =>
    const SuperAdminUserManagementPreviewPage(),
  'super-admin-warehouse-automation.html' =>
    const SuperAdminWarehouseAutomationPreviewPage(),
  _ => throw ArgumentError.value(
    spec.fileName,
    'spec.fileName',
    'Unknown preview',
  ),
};

class AgentAddProductPreviewPage extends StatelessWidget {
  const AgentAddProductPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      const SourcingAgentProductManagementPage();
}

class AgentAgizishaOrdersPreviewPage extends StatelessWidget {
  const AgentAgizishaOrdersPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-agizisha-orders.html').role,
    title: nativeScreenSpecFor('agent-agizisha-orders.html').title,
    endpoint: 'sourcing_agent/agizisha-orders',
  );
}

class AgentBatchDetailsPreviewPage extends StatelessWidget {
  const AgentBatchDetailsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentBatchFinancialsPreviewPage extends StatelessWidget {
  const AgentBatchFinancialsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentBatchesPreviewPage extends StatelessWidget {
  const AgentBatchesPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentContainerDetailPreviewPage extends StatelessWidget {
  const AgentContainerDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => PreviewPageLayout(
    spec: nativeScreenSpecFor('agent-container-detail.html'),
  );
}

class AgentContainersPreviewPage extends StatelessWidget {
  const AgentContainersPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-containers.html').role,
    title: nativeScreenSpecFor('agent-containers.html').title,
    endpoint: 'sourcing_agent/containers',
  );
}

class AgentCreateBatchPreviewPage extends StatelessWidget {
  const AgentCreateBatchPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentCreateBatchPage();
}

class AgentCreatePackingListPreviewPage extends StatelessWidget {
  const AgentCreatePackingListPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentDashboardPreviewPage extends StatelessWidget {
  const AgentDashboardPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentDashboardPage();
}

class AgentExpressAirCargoPreviewPage extends StatelessWidget {
  const AgentExpressAirCargoPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-express-air-cargo.html').role,
    title: nativeScreenSpecFor('agent-express-air-cargo.html').title,
    endpoint: 'sourcing_agent/express-air-cargo/bookings',
  );
}

class AgentFinancialsPreviewPage extends StatelessWidget {
  const AgentFinancialsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-financials.html').role,
    title: nativeScreenSpecFor('agent-financials.html').title,
    endpoint: 'sourcing_agent/financials',
  );
}

class AgentGenerateOrdersPreviewPage extends StatelessWidget {
  const AgentGenerateOrdersPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentNotificationsPreviewPage extends StatelessWidget {
  const AgentNotificationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentNotificationsPage();
}

class AgentOrderDetailPreviewPage extends StatelessWidget {
  const AgentOrderDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentPackingListDetailPreviewPage extends StatelessWidget {
  const AgentPackingListDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentPackingListsPreviewPage extends StatelessWidget {
  const AgentPackingListsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentBatchListPage();
}

class AgentPendingApprovalPreviewPage extends StatelessWidget {
  const AgentPendingApprovalPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SourcingAgentDashboardPage();
}

class AgentProductManagementPreviewPage extends StatelessWidget {
  const AgentProductManagementPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      const SourcingAgentProductManagementPage();
}

class AgentReservationsPreviewPage extends StatelessWidget {
  const AgentReservationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-reservations.html').role,
    title: nativeScreenSpecFor('agent-reservations.html').title,
    endpoint: 'sourcing_agent/reservations',
  );
}

class AgentStorefrontPreviewPage extends StatelessWidget {
  const AgentStorefrontPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-storefront.html').role,
    title: nativeScreenSpecFor('agent-storefront.html').title,
    endpoint: 'sourcing_agent/public-profile',
  );
}

class AgentTrackShipmentPreviewPage extends StatelessWidget {
  const AgentTrackShipmentPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('agent-track-shipment.html').role,
    title: nativeScreenSpecFor('agent-track-shipment.html').title,
    endpoint: 'tracking/agent/shipment_orders',
  );
}

class CargoAdminContainerManagementPreviewPage extends StatelessWidget {
  const CargoAdminContainerManagementPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CargoAdminContainerListPage();
}

class CargoAdminCustomerManagementPreviewPage extends StatelessWidget {
  const CargoAdminCustomerManagementPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-customer-management.html').role,
    title: nativeScreenSpecFor('cargo-admin-customer-management.html').title,
    endpoint: 'cargo_admin/customers',
  );
}

class CargoAdminDashboardPreviewPage extends StatelessWidget {
  const CargoAdminDashboardPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CargoAdminDashboardPage();
}

class CargoAdminDocumentationWorkspacePreviewPage extends StatelessWidget {
  const CargoAdminDocumentationWorkspacePreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      const CargoAdminDocumentationWorkspacePage();
}

class CargoAdminExpressAirCargoPreviewPage extends StatelessWidget {
  const CargoAdminExpressAirCargoPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-express-air-cargo.html').role,
    title: nativeScreenSpecFor('cargo-admin-express-air-cargo.html').title,
    endpoint: 'cargo_admin/express-air-cargo/bookings',
  );
}

class CargoAdminFclRequestsPreviewPage extends StatelessWidget {
  const CargoAdminFclRequestsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-fcl-requests.html').role,
    title: nativeScreenSpecFor('cargo-admin-fcl-requests.html').title,
    endpoint: 'cargo_admin/fcl-requests',
  );
}

class CargoAdminManualIntakePreviewPage extends StatelessWidget {
  const CargoAdminManualIntakePreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CargoAdminManualIntakePage();
}

class CargoAdminNotificationsPreviewPage extends StatelessWidget {
  const CargoAdminNotificationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-notifications.html').role,
    title: nativeScreenSpecFor('cargo-admin-notifications.html').title,
    endpoint: 'cargo_admin/notifications',
  );
}

class CargoAdminPackingListsPreviewPage extends StatelessWidget {
  const CargoAdminPackingListsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CargoAdminPackingListsPage();
}

class CargoAdminReceiptsPreviewPage extends StatelessWidget {
  const CargoAdminReceiptsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CargoAdminReceiptsPage();
}

class CargoAdminReservationsPreviewPage extends StatelessWidget {
  const CargoAdminReservationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-reservations.html').role,
    title: nativeScreenSpecFor('cargo-admin-reservations.html').title,
    endpoint: 'cargo_admin/reservations',
  );
}

class CargoAdminShipmentOrdersPreviewPage extends StatelessWidget {
  const CargoAdminShipmentOrdersPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-shipment-orders.html').role,
    title: nativeScreenSpecFor('cargo-admin-shipment-orders.html').title,
    endpoint: 'cargo_admin/shipment-orders',
  );
}

class CargoAdminTrackShipmentPreviewPage extends StatelessWidget {
  const CargoAdminTrackShipmentPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-track-shipment.html').role,
    title: nativeScreenSpecFor('cargo-admin-track-shipment.html').title,
    endpoint: 'tracking/admin/shipment_orders',
  );
}

class CargoAdminWarehouseAutomationPreviewPage extends StatelessWidget {
  const CargoAdminWarehouseAutomationPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      const CargoAdminWarehouseAutomationPage();
}

class CargoAdminWarehousesPreviewPage extends StatelessWidget {
  const CargoAdminWarehousesPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('cargo-admin-warehouses.html').role,
    title: nativeScreenSpecFor('cargo-admin-warehouses.html').title,
    endpoint: 'cargo_admin/warehouses',
  );
}

class CustomerAgizishaPreviewPage extends StatelessWidget {
  const CustomerAgizishaPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerOrderListPage();
}

class CustomerBookingConfirmationPreviewPage extends StatelessWidget {
  const CustomerBookingConfirmationPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ContainerListPage();
}

class CustomerChinaAddressesPreviewPage extends StatelessWidget {
  const CustomerChinaAddressesPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ChinaAddressListPage();
}

class CustomerCollectionCodePreviewPage extends StatelessWidget {
  const CustomerCollectionCodePreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('customer-collection-code.html').role,
    title: nativeScreenSpecFor('customer-collection-code.html').title,
    endpoint: 'customer/reservations',
  );
}

class CustomerContainerDetailsPreviewPage extends StatelessWidget {
  const CustomerContainerDetailsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ContainerListPage();
}

class CustomerDashboardPreviewPage extends StatelessWidget {
  const CustomerDashboardPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerShell();
}

class CustomerDocumentsPreviewPage extends StatelessWidget {
  const CustomerDocumentsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerDocumentsPage();
}

class CustomerExpressAirCargoPreviewPage extends StatelessWidget {
  const CustomerExpressAirCargoPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const AirCargoBookingListPage();
}

class CustomerLoginPreviewPage extends StatelessWidget {
  const CustomerLoginPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SignInPage();
}

class CustomerNotificationsPreviewPage extends StatelessWidget {
  const CustomerNotificationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerNotificationsPage();
}

class CustomerOrderDetailsPreviewPage extends StatelessWidget {
  const CustomerOrderDetailsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('customer-order-details.html').role,
    title: nativeScreenSpecFor('customer-order-details.html').title,
    endpoint: 'customer/orders',
  );
}

class CustomerOrdersPreviewPage extends StatelessWidget {
  const CustomerOrdersPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerOrderListPage();
}

class CustomerOtpPreviewPage extends StatelessWidget {
  const CustomerOtpPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SignInPage();
}

class CustomerPackingListPreviewPage extends StatelessWidget {
  const CustomerPackingListPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerPackingListPage();
}

class CustomerProfilePreviewPage extends StatelessWidget {
  const CustomerProfilePreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const CustomerProfilePage();
}

class CustomerRegisterPreviewPage extends StatelessWidget {
  const CustomerRegisterPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SignInPage();
}

class CustomerReservationDetailPreviewPage extends StatelessWidget {
  const CustomerReservationDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ReservationListPage();
}

class CustomerReservationsPreviewPage extends StatelessWidget {
  const CustomerReservationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ReservationListPage();
}

class CustomerReserveCbmPreviewPage extends StatelessWidget {
  const CustomerReserveCbmPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ContainerListPage();
}

class CustomerSearchContainerPreviewPage extends StatelessWidget {
  const CustomerSearchContainerPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ContainerListPage();
}

class CustomerShipmentOrderDetailPreviewPage extends StatelessWidget {
  const CustomerShipmentOrderDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ShipmentListPage();
}

class CustomerShipmentTrackingPreviewPage extends StatelessWidget {
  const CustomerShipmentTrackingPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const ShipmentTrackingPage();
}

class CustomerSplashPreviewPage extends StatelessWidget {
  const CustomerSplashPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const WelcomePage();
}

class CustomerWarehouseParcelsPreviewPage extends StatelessWidget {
  const CustomerWarehouseParcelsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => PreviewPageLayout(
    spec: nativeScreenSpecFor('customer-warehouse-parcels.html'),
  );
}

class PublicAboutPreviewPage extends StatelessWidget {
  const PublicAboutPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-about.html'));
}

class PublicAccessibilityPreviewPage extends StatelessWidget {
  const PublicAccessibilityPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-accessibility.html'));
}

class PublicAgizishaAgentStorefrontPreviewPage extends StatelessWidget {
  const PublicAgizishaAgentStorefrontPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-agizisha-agent-storefront.html').role,
    title: nativeScreenSpecFor('public-agizisha-agent-storefront.html').title,
    endpoint: 'public/agizisha/agents',
  );
}

class PublicAgizishaCataloguePreviewPage extends StatelessWidget {
  const PublicAgizishaCataloguePreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-agizisha-catalogue.html').role,
    title: nativeScreenSpecFor('public-agizisha-catalogue.html').title,
    endpoint: 'public/agizisha/products',
  );
}

class PublicAgizishaProductDetailPreviewPage extends StatelessWidget {
  const PublicAgizishaProductDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-agizisha-product-detail.html').role,
    title: nativeScreenSpecFor('public-agizisha-product-detail.html').title,
    endpoint: 'public/agizisha/products',
  );
}

class PublicAirCargoPreviewPage extends StatelessWidget {
  const PublicAirCargoPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-air-cargo.html').role,
    title: nativeScreenSpecFor('public-air-cargo.html').title,
    endpoint: 'public/air-departure-schedules',
  );
}

class PublicContactPreviewPage extends StatelessWidget {
  const PublicContactPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-contact.html'));
}

class PublicContainersPreviewPage extends StatelessWidget {
  const PublicContainersPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const PublicContainersPage();
}

class PublicCookiesPreviewPage extends StatelessWidget {
  const PublicCookiesPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-cookies.html'));
}

class PublicFaqPreviewPage extends StatelessWidget {
  const PublicFaqPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-faq.html'));
}

class PublicFclQuoteRequestPreviewPage extends StatelessWidget {
  const PublicFclQuoteRequestPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => ApiFormPage(
    role: 'Public',
    title: 'Request an FCL quote',
    endpoint: 'fcl-quote-request',
    fields: [
      ApiFormField(name: 'product', label: 'Product', required: true),
      ApiFormField(
        name: 'specifications',
        label: 'Specifications',
        required: true,
        multiline: true,
      ),
      ApiFormField(
        name: 'supplier_status',
        label: 'Supplier status',
        required: true,
      ),
      ApiFormField(name: 'incoterm', label: 'Incoterm', required: true),
      ApiFormField(name: 'destination', label: 'Destination', required: true),
      ApiFormField(name: 'company_name', label: 'Company name', required: true),
      ApiFormField(
        name: 'business_license',
        label: 'Business license',
        required: true,
      ),
      ApiFormField(name: 'email', label: 'Email', required: true),
      ApiFormField(
        name: 'whatsapp_number',
        label: 'WhatsApp number',
        required: true,
      ),
    ],
  );
}

class PublicFeedbackPreviewPage extends StatelessWidget {
  const PublicFeedbackPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-feedback.html'));
}

class PublicHowItWorksPreviewPage extends StatelessWidget {
  const PublicHowItWorksPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-how-it-works.html'));
}

class PublicLandingPreviewPage extends StatelessWidget {
  const PublicLandingPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-landing.html').role,
    title: nativeScreenSpecFor('public-landing.html').title,
    endpoint: 'public/platform-stats',
  );
}

class PublicLegalPreviewPage extends StatelessWidget {
  const PublicLegalPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-legal.html'));
}

class PublicPricingPreviewPage extends StatelessWidget {
  const PublicPricingPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-pricing.html'));
}

class PublicPrivacyPreviewPage extends StatelessWidget {
  const PublicPrivacyPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-privacy.html'));
}

class PublicReceiptVerificationPreviewPage extends StatelessWidget {
  const PublicReceiptVerificationPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => PreviewPageLayout(
    spec: nativeScreenSpecFor('public-receipt-verification.html'),
  );
}

class PublicSharedBatchPreviewPage extends StatelessWidget {
  const PublicSharedBatchPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-shared-batch.html'));
}

class PublicSitemapPreviewPage extends StatelessWidget {
  const PublicSitemapPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-sitemap.html'));
}

class PublicSourcingAgentRegistrationPreviewPage extends StatelessWidget {
  const PublicSourcingAgentRegistrationPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => ApiFormPage(
    role: 'Public',
    title: 'Become a sourcing agent',
    endpoint: 'public/sourcing-agents/register',
    multipart: true,
    fields: [
      ApiFormField(name: 'full_name', label: 'Full name', required: true),
      ApiFormField(name: 'phone', label: 'Phone', required: true),
      ApiFormField(name: 'email', label: 'Email', required: true),
      ApiFormField(name: 'whatsapp', label: 'WhatsApp'),
      ApiFormField(name: 'instagram', label: 'Instagram'),
      ApiFormField(name: 'tiktok', label: 'TikTok'),
      ApiFormField(name: 'niche', label: 'Sourcing niche', required: true),
      ApiFormField(name: 'location', label: 'Location', required: true),
      ApiFormField(name: 'bio', label: 'About you', multiline: true),
      ApiFormField(
        name: 'years_experience',
        label: 'Years of experience',
        numeric: true,
      ),
    ],
  );
}

class PublicSupportTicketsPreviewPage extends StatelessWidget {
  const PublicSupportTicketsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => PreviewPageLayout(
    spec: nativeScreenSpecFor('public-support-tickets.html'),
  );
}

class PublicSupportPreviewPage extends StatelessWidget {
  const PublicSupportPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-support.html'));
}

class PublicTermsPreviewPage extends StatelessWidget {
  const PublicTermsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('public-terms.html'));
}

class PublicWarehouseDetailPreviewPage extends StatelessWidget {
  const PublicWarehouseDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-warehouse-detail.html').role,
    title: nativeScreenSpecFor('public-warehouse-detail.html').title,
    endpoint: 'cargo_admin/public/warehouses/search',
  );
}

class PublicWarehousesPreviewPage extends StatelessWidget {
  const PublicWarehousesPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('public-warehouses.html').role,
    title: nativeScreenSpecFor('public-warehouses.html').title,
    endpoint: 'cargo_admin/public/warehouses/search',
  );
}

class SharedAirShippingLabelPreviewPage extends StatelessWidget {
  const SharedAirShippingLabelPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => PreviewPageLayout(
    spec: nativeScreenSpecFor('shared-air-shipping-label.html'),
  );
}

class SharedProductDetailPreviewPage extends StatelessWidget {
  const SharedProductDetailPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('shared-product-detail.html').role,
    title: nativeScreenSpecFor('shared-product-detail.html').title,
    endpoint: 'public/agizisha/products',
  );
}

class SharedSeaShippingLabelPreviewPage extends StatelessWidget {
  const SharedSeaShippingLabelPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => PreviewPageLayout(
    spec: nativeScreenSpecFor('shared-sea-shipping-label.html'),
  );
}

class SuperAdminApprovalsPreviewPage extends StatelessWidget {
  const SuperAdminApprovalsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('super-admin-approvals.html').role,
    title: nativeScreenSpecFor('super-admin-approvals.html').title,
    endpoint: 'super_admin/users/pending',
  );
}

class SuperAdminCommissionPreviewPage extends StatelessWidget {
  const SuperAdminCommissionPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => ApiFormPage(
    role: 'Super Admin',
    title: 'Commission settings',
    endpoint: 'super_admin/commission',
    fields: [
      ApiFormField(
        name: 'commission_percentage',
        label: 'Commission percentage',
        required: true,
        numeric: true,
      ),
    ],
  );
}

class SuperAdminDashboardPreviewPage extends StatelessWidget {
  const SuperAdminDashboardPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SuperAdminDashboardPage();
}

class SuperAdminGoodsClassificationPreviewPage extends StatelessWidget {
  const SuperAdminGoodsClassificationPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => ApiFormPage(
    role: 'Super Admin',
    title: 'Create goods category',
    endpoint: 'super_admin/goods/categories',
    fields: [
      ApiFormField(name: 'name', label: 'Category name', required: true),
      ApiFormField(name: 'description', label: 'Description', multiline: true),
    ],
  );
}

class SuperAdminNotificationsPreviewPage extends StatelessWidget {
  const SuperAdminNotificationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('super-admin-notifications.html').role,
    title: nativeScreenSpecFor('super-admin-notifications.html').title,
    endpoint: 'super_admin/notifications',
  );
}

class SuperAdminOperatorsPreviewPage extends StatelessWidget {
  const SuperAdminOperatorsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('super-admin-operators.html').role,
    title: nativeScreenSpecFor('super-admin-operators.html').title,
    endpoint: 'super_admin/operators',
  );
}

class SuperAdminPlatformActivityPreviewPage extends StatelessWidget {
  const SuperAdminPlatformActivityPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SuperAdminPlatformActivityPage();
}

class SuperAdminReservationsPreviewPage extends StatelessWidget {
  const SuperAdminReservationsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('super-admin-reservations.html').role,
    title: nativeScreenSpecFor('super-admin-reservations.html').title,
    endpoint: 'super_admin/reservations',
  );
}

class SuperAdminSettingsPreviewPage extends StatelessWidget {
  const SuperAdminSettingsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      PreviewPageLayout(spec: nativeScreenSpecFor('super-admin-settings.html'));
}

class SuperAdminSourcingAgentsPreviewPage extends StatelessWidget {
  const SuperAdminSourcingAgentsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('super-admin-sourcing-agents.html').role,
    title: nativeScreenSpecFor('super-admin-sourcing-agents.html').title,
    endpoint: 'super_admin/sourcing-agents',
  );
}

class SuperAdminTrackShipmentPreviewPage extends StatelessWidget {
  const SuperAdminTrackShipmentPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => LiveWorkflowPage(
    role: nativeScreenSpecFor('super-admin-track-shipment.html').role,
    title: nativeScreenSpecFor('super-admin-track-shipment.html').title,
    endpoint: 'tracking/admin/shipment_orders',
  );
}

class SuperAdminUserDetailsPreviewPage extends StatelessWidget {
  const SuperAdminUserDetailsPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SuperAdminUserListPage();
}

class SuperAdminUserManagementPreviewPage extends StatelessWidget {
  const SuperAdminUserManagementPreviewPage({super.key});

  @override
  Widget build(BuildContext context) => const SuperAdminUserListPage();
}

class SuperAdminWarehouseAutomationPreviewPage extends StatelessWidget {
  const SuperAdminWarehouseAutomationPreviewPage({super.key});

  @override
  Widget build(BuildContext context) =>
      const SuperAdminWarehouseAutomationPage();
}
