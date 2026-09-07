import 'dart:typed_data';

import '../../../../core/network/api_client.dart';

class SourcingAgentBatchesRepository {
  SourcingAgentBatchesRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> listBatches() =>
      client.getObject('sourcing_agent/batches');

  Future<Map<String, dynamic>> getBatch(String batchId) =>
      client.getObject('sourcing_agent/batches/$batchId');

  Future<Map<String, dynamic>> listOrders(String batchId) =>
      client.getObject('sourcing_agent/batches/$batchId/orders');

  Future<Map<String, dynamic>> createBatch({
    required String title,
    String? description,
    required String currency,
    required String shippingMethod,
    double? shippingFeePerCbm,
  }) => client.post<Map<String, dynamic>>(
    'sourcing_agent/batches',
    data: {
      'title': title,
      'description': description,
      'currency': currency,
      'shipping_method': shippingMethod,
      'shipping_fee_per_cbm': shippingFeePerCbm,
    },
  );

  Future<Map<String, dynamic>> createPackingList({
    required String batchId,
    required String name,
    String? description,
  }) => client.post<Map<String, dynamic>>(
    'sourcing_agent/batches/$batchId/packing-lists',
    data: {'name': name, 'description': description},
  );

  Future<Map<String, dynamic>> createProduct({
    required String batchId,
    required String goodsTypeId,
    required String name,
    String? description,
    required double pricePerUnit,
    required int minimumOrderQuantity,
    required String imageUrl,
  }) => client.post<Map<String, dynamic>>(
    'sourcing_agent/batches/$batchId/products',
    data: {
      'goods_type_id': goodsTypeId,
      'name': name,
      'description': description,
      'price_per_unit': pricePerUnit,
      'minimum_order_quantity': minimumOrderQuantity,
      'image_url': imageUrl,
      'status': 'draft',
    },
  );

  Future<Map<String, dynamic>> listGoodsCategories() =>
      client.getObject('sourcing_agent/goods/categories');

  Future<List<Map<String, dynamic>>> listProducts(String batchId) =>
      client.getList('sourcing_agent/batches/$batchId/products');

  Future<Map<String, dynamic>> updateProduct({
    required String batchId,
    required String productId,
    String? name,
    String? description,
    double? pricePerUnit,
    int? minimumOrderQuantity,
    String? imageUrl,
    String? status,
  }) =>
      client.patch<Map<String, dynamic>>(
        'sourcing_agent/batches/$batchId/products/$productId',
        data: {
          if (name != null) 'name': name,
          if (description != null) 'description': description,
          if (pricePerUnit != null) 'price_per_unit': pricePerUnit,
          if (minimumOrderQuantity != null)
            'minimum_order_quantity': minimumOrderQuantity,
          if (imageUrl != null) 'image_url': imageUrl,
          if (status != null) 'status': status,
        },
      );

  // ── Containers & CBM bookings ─────────────────────────
  Future<List<Map<String, dynamic>>> listAvailableContainers() =>
      client.getList('sourcing_agent/containers/available');

  Future<Map<String, dynamic>> bookCbm({
    required String containerId,
    required double cbmAmount,
    required String destinationCity,
    String? destinationCountry,
  }) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/containers/book-cbm',
        data: {
          'container_id': containerId,
          'cbm_amount': cbmAmount,
          'destination_city': destinationCity,
          if (destinationCountry != null) 'destination_country': destinationCountry,
        },
      );

  Future<List<Map<String, dynamic>>> listSeaBookings() =>
      client.getList('sourcing_agent/sea-bookings');

  // ── Invoices & receipts ───────────────────────────────
  Future<List<Map<String, dynamic>>> listInvoices() async {
    final res = await client.getObject('sourcing_agent/invoices');
    return (res['invoices'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> listReceipts() async {
    final res = await client.getObject('sourcing_agent/receipts');
    return (res['receipts'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
  }

  // ── Financials ────────────────────────────────────────
  Future<Map<String, dynamic>> getFinancials() =>
      client.getObject('sourcing_agent/financials');

  Future<Map<String, dynamic>> getBatchFinancials(String batchId) =>
      client.getObject('sourcing_agent/batches/$batchId/financials');

  // ── Share ─────────────────────────────────────────────
  Future<Map<String, dynamic>> shareBatch({
    required String batchId,
    int? expiresDays,
    int? maxViews,
  }) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/batches/$batchId/share',
        data: {
          if (expiresDays != null) 'expires_days': expiresDays,
          if (maxViews != null) 'max_views': maxViews,
        },
      );

  Future<Map<String, dynamic>> shareInvoice(String orderId) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/orders/$orderId/share-invoice',
      );

  // ── Orders ────────────────────────────────────────────
  Future<Map<String, dynamic>> updateOrderPaymentStatus({
    required String orderId,
    required String paymentStatus,
  }) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/orders/$orderId/update-payment-status',
        queryParameters: {'payment_status': paymentStatus},
      );

  // ── Express air cargo ─────────────────────────────────
  Future<Map<String, dynamic>> getAirCargoOptions() =>
      client.getObject('sourcing_agent/express-air-cargo/options');

  Future<Map<String, dynamic>> bookAirCargo({
    required String cargoTypeId,
    required double weightKg,
    required DateTime shipmentDate,
    required String destinationRegion,
    String destinationCountry = 'Tanzania',
    int cartonCount = 1,
    String? cargoDescription,
    String? airCargoRateId,
  }) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/express-air-cargo/book',
        data: {
          'cargo_type_id': cargoTypeId,
          'weight_kg': weightKg,
          'shipment_date': shipmentDate.toIso8601String(),
          'destination_region': destinationRegion,
          'destination_country': destinationCountry,
          'carton_count': cartonCount,
          if (cargoDescription != null) 'cargo_description': cargoDescription,
          if (airCargoRateId != null) 'air_cargo_rate_id': airCargoRateId,
        },
      );

  Future<List<Map<String, dynamic>>> listAirBookings() =>
      client.getList('sourcing_agent/express-air-cargo/bookings');

  Future<Map<String, dynamic>> getAirShippingLabel(String bookingId) =>
      client.getObject('sourcing_agent/express-air-cargo/$bookingId/shipping-label');

  Future<Map<String, dynamic>> updateAirShippingLabel(
    String bookingId,
    Map<String, dynamic> data,
  ) =>
      client.patch<Map<String, dynamic>>(
        'sourcing_agent/express-air-cargo/$bookingId/shipping-label',
        data: data,
      );

  // ── Product attributes & instagram ────────────────────
  Future<Map<String, dynamic>> getAttributeTemplates(String goodsTypeId) =>
      client.getObject('sourcing_agent/goods/types/$goodsTypeId/attribute-templates');

  Future<Map<String, dynamic>> importInstagramImage({
    required String batchId,
    required String instagramUrl,
    int? imageIndex,
  }) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/batches/$batchId/products/import-instagram',
        data: {
          'instagram_url': instagramUrl,
          if (imageIndex != null) 'image_index': imageIndex,
        },
      );

  // ── Packing lists (detail, items, exports) ────────────
  Future<Map<String, dynamic>> listPackingLists() =>
      client.getObject('sourcing_agent/packing-lists');

  Future<Map<String, dynamic>> getPackingList(String packingListId) =>
      client.getObject('sourcing_agent/packing-lists/$packingListId');

  Future<Map<String, dynamic>> addPackingListItem({
    required String packingListId,
    required String itemName,
    required double pricePerPiece,
    required int cartons,
    required int itemsPerCarton,
    required double cbmPerCarton,
    required double kilogramPerCarton,
    String? itemCode,
    String? itemPicture,
  }) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/packing-lists/$packingListId/items',
        data: {
          'item_name': itemName,
          'price_per_piece': pricePerPiece,
          'item_code': itemCode,
          'item_picture': itemPicture,
          'cartons': cartons,
          'items_per_carton': itemsPerCarton,
          'cbm_per_carton': cbmPerCarton,
          'kilogram_per_carton': kilogramPerCarton,
        },
      );

  Future<Map<String, dynamic>> updatePackingListItem({
    required String itemId,
    String? itemName,
    double? pricePerPiece,
    int? cartons,
    int? itemsPerCarton,
    double? cbmPerCarton,
    double? kilogramPerCarton,
    String? itemCode,
    String? itemPicture,
  }) =>
      client.put<Map<String, dynamic>>(
        'sourcing_agent/packing-list-items/$itemId',
        data: {
          if (itemName != null) 'item_name': itemName,
          if (pricePerPiece != null) 'price_per_piece': pricePerPiece,
          if (itemCode != null) 'item_code': itemCode,
          if (itemPicture != null) 'item_picture': itemPicture,
          if (cartons != null) 'cartons': cartons,
          if (itemsPerCarton != null) 'items_per_carton': itemsPerCarton,
          if (cbmPerCarton != null) 'cbm_per_carton': cbmPerCarton,
          if (kilogramPerCarton != null) 'kilogram_per_carton': kilogramPerCarton,
        },
      );

  Future<Uint8List> exportPackingListPdf(String packingListId) =>
      client.downloadBytes('sourcing_agent/packing-lists/$packingListId/export/pdf');

  Future<Uint8List> exportPackingListExcel(String packingListId) =>
      client.downloadBytes('sourcing_agent/packing-lists/$packingListId/export/excel');

  // ── Invoices & receipts ───────────────────────────────
  Future<Uint8List> downloadPublicDocument(String url) =>
      client.downloadPublicBytes(url);

  Future<Map<String, dynamic>> generateReceipt(String orderId, {String format = 'pdf'}) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/orders/$orderId/generate-receipt',
        queryParameters: {'format': format},
      );

  Future<Map<String, dynamic>> generateInvoice(String orderId, {String format = 'pdf'}) =>
      client.post<Map<String, dynamic>>(
        'sourcing_agent/orders/$orderId/generate-invoice',
        queryParameters: {'format': format},
      );
}
