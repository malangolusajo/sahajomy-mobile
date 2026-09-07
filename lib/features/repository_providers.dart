import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/providers.dart';
import 'cargo_admin/containers/data/cargo_admin_containers_repository.dart';
import 'cargo_admin/dashboard/data/cargo_admin_dashboard_repository.dart';
import 'cargo_admin/documents/data/cargo_admin_documents_repository.dart';
import 'cargo_admin/operations/data/cargo_operations_repository.dart';
import 'cargo_admin/warehouse_automation/data/warehouse_automation_repository.dart';
import 'booking/data/guided_booking_repository.dart';
import 'customer/air_cargo/data/customer_air_cargo_repository.dart';
import 'customer/china_addresses/data/customer_china_addresses_repository.dart';
import 'customer/containers/data/customer_containers_repository.dart';
import 'customer/dashboard/data/customer_dashboard_repository.dart';
import 'customer/fcl_quote/data/customer_fcl_quote_repository.dart';
import 'customer/notifications/data/customer_notifications_repository.dart';
import 'customer/orders/data/customer_orders_repository.dart';
import 'customer/orders/data/customer_sourcing_repository.dart';
import 'customer/bookings/data/customer_booking_repository.dart';
import 'customer/shipments/data/customer_shipments_repository.dart';
import 'customer/tracking/data/customer_tracking_repository.dart';
import 'customer/warehouse_access/data/customer_warehouse_access_repository.dart';
import 'public_services/data/public_services_repository.dart';
import 'reference/data/workflow_api_repository.dart';
import 'sourcing_agent/batches/data/sourcing_agent_batches_repository.dart';
import 'super_admin/dashboard/data/super_admin_dashboard_repository.dart';
import 'super_admin/users/data/super_admin_users_repository.dart';
import 'super_admin/warehouse_automation/data/super_admin_warehouse_automation_repository.dart';

final cargoAdminContainersRepositoryProvider =
    Provider<CargoAdminContainersRepository>(
      (ref) =>
          CargoAdminContainersRepository(client: ref.watch(apiClientProvider)),
    );

final cargoAdminDashboardRepositoryProvider =
    Provider<CargoAdminDashboardRepository>(
      (ref) =>
          CargoAdminDashboardRepository(client: ref.watch(apiClientProvider)),
    );

final cargoAdminDocumentsRepositoryProvider =
    Provider<CargoAdminDocumentsRepository>(
      (ref) =>
          CargoAdminDocumentsRepository(client: ref.watch(apiClientProvider)),
    );

final warehouseAutomationRepositoryProvider =
    Provider<WarehouseAutomationRepository>(
      (ref) =>
          WarehouseAutomationRepository(client: ref.watch(apiClientProvider)),
    );

final cargoOperationsRepositoryProvider = Provider<CargoOperationsRepository>(
  (ref) => CargoOperationsRepository(client: ref.watch(apiClientProvider)),
);

final customerAirCargoRepositoryProvider = Provider<CustomerAirCargoRepository>(
  (ref) => CustomerAirCargoRepository(client: ref.watch(apiClientProvider)),
);

final guidedBookingRepositoryProvider = Provider<GuidedBookingRepository>(
  (ref) => GuidedBookingRepository(client: ref.watch(apiClientProvider)),
);

final customerChinaAddressesRepositoryProvider =
    Provider<CustomerChinaAddressesRepository>(
      (ref) => CustomerChinaAddressesRepository(
        client: ref.watch(apiClientProvider),
      ),
    );

final customerContainersRepositoryProvider =
    Provider<CustomerContainersRepository>(
      (ref) =>
          CustomerContainersRepository(client: ref.watch(apiClientProvider)),
    );

final customerDashboardRepositoryProvider =
    Provider<CustomerDashboardRepository>(
      (ref) =>
          CustomerDashboardRepository(client: ref.watch(apiClientProvider)),
    );

final customerNotificationsRepositoryProvider =
    Provider<CustomerNotificationsRepository>(
      (ref) =>
          CustomerNotificationsRepository(client: ref.watch(apiClientProvider)),
    );

final customerOrdersRepositoryProvider = Provider<CustomerOrdersRepository>(
  (ref) => CustomerOrdersRepository(client: ref.watch(apiClientProvider)),
);

final customerBookingRepositoryProvider = Provider<CustomerBookingRepository>(
  (ref) => CustomerBookingRepository(client: ref.watch(apiClientProvider)),
);

final customerFclQuoteRepositoryProvider = Provider<CustomerFclQuoteRepository>(
  (ref) => CustomerFclQuoteRepository(client: ref.watch(apiClientProvider)),
);

final customerSourcingRepositoryProvider = Provider<CustomerSourcingRepository>(
  (ref) => CustomerSourcingRepository(client: ref.watch(apiClientProvider)),
);

final customerShipmentsRepositoryProvider =
    Provider<CustomerShipmentsRepository>(
      (ref) =>
          CustomerShipmentsRepository(client: ref.watch(apiClientProvider)),
    );

final customerTrackingRepositoryProvider = Provider<CustomerTrackingRepository>(
  (ref) => CustomerTrackingRepository(client: ref.watch(apiClientProvider)),
);

final customerWarehouseAccessRepositoryProvider =
    Provider<CustomerWarehouseAccessRepository>(
      (ref) => CustomerWarehouseAccessRepository(
        client: ref.watch(apiClientProvider),
      ),
    );

final publicServicesRepositoryProvider = Provider<PublicServicesRepository>(
  (ref) => PublicServicesRepository(client: ref.watch(apiClientProvider)),
);

final workflowApiRepositoryProvider = Provider<WorkflowApiRepository>(
  (ref) => WorkflowApiRepository(client: ref.watch(apiClientProvider)),
);

final sourcingAgentBatchesRepositoryProvider =
    Provider<SourcingAgentBatchesRepository>(
      (ref) =>
          SourcingAgentBatchesRepository(client: ref.watch(apiClientProvider)),
    );

final superAdminDashboardRepositoryProvider =
    Provider<SuperAdminDashboardRepository>(
      (ref) =>
          SuperAdminDashboardRepository(client: ref.watch(apiClientProvider)),
    );

final superAdminUsersRepositoryProvider = Provider<SuperAdminUsersRepository>(
  (ref) => SuperAdminUsersRepository(client: ref.watch(apiClientProvider)),
);

final superAdminWarehouseAutomationRepositoryProvider =
    Provider<SuperAdminWarehouseAutomationRepository>(
      (ref) => SuperAdminWarehouseAutomationRepository(
        client: ref.watch(apiClientProvider),
      ),
    );
