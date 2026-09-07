import 'package:flutter/material.dart';

import '../../documents/presentation/cargo_admin_documentation_workspace_page.dart';
import 'customs_packing_list_detail_page.dart';

/// Customs routes are packing-list operations in the current FastAPI
/// contract. These route adapters retain existing deep links while opening
/// the authoritative list/detail workflow.
class CargoCustomsDashboardPage extends StatelessWidget {
  const CargoCustomsDashboardPage({super.key});

  @override
  Widget build(BuildContext context) => const CargoAdminPackingListsPage();
}

class CargoCustomsShipmentPage extends StatelessWidget {
  const CargoCustomsShipmentPage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) =>
      CustomsPackingListDetailPage(packingListId: shipmentId);
}

class CargoCustomsDocumentsPage extends StatelessWidget {
  const CargoCustomsDocumentsPage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) =>
      CustomsPackingListDetailPage(packingListId: shipmentId);
}

class CargoCustomsUpdateStatusPage extends StatelessWidget {
  const CargoCustomsUpdateStatusPage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) =>
      CustomsPackingListDetailPage(packingListId: shipmentId);
}

class CargoCustomsReleasePage extends StatelessWidget {
  const CargoCustomsReleasePage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) =>
      CustomsPackingListDetailPage(packingListId: shipmentId);
}
