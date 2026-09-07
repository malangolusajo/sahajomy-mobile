import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../../core/utils/document_handler.dart';
import '../../../customer/presentation/customer_components.dart';
import '../../../repository_providers.dart';
import '../../batches/data/sourcing_agent_batches_repository.dart';

/// Screen 103 — Update payment status
class AgentUpdatePaymentStatusPage extends ConsumerStatefulWidget {
  const AgentUpdatePaymentStatusPage({required this.orderId, required this.customerName, super.key});
  final String orderId;
  final String customerName;

  @override
  ConsumerState<AgentUpdatePaymentStatusPage> createState() => _AgentUpdatePaymentStatusPageState();
}

class _AgentUpdatePaymentStatusPageState extends ConsumerState<AgentUpdatePaymentStatusPage> {
  String _status = 'unpaid';
  bool _busy = false;

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await ref.read(sourcingAgentBatchesRepositoryProvider).updateOrderPaymentStatus(
        orderId: widget.orderId,
        paymentStatus: _status,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Payment marked as $_status')));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'PAYMENT',
    title: 'Update payment status',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        CustomerHeroCard(eyebrow: widget.customerName, title: 'Order payment', subtitle: 'Mark this order as paid or unpaid.'),
        const SizedBox(height: 20),
        const Text('Payment status', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
        const SizedBox(height: 8),
        RadioGroup<String>(
          groupValue: _status,
          onChanged: (v) => setState(() => _status = v ?? 'unpaid'),
          child: Column(
            children: ['unpaid', 'paid'].map((s) => RadioListTile<String>(
              value: s,
              title: Text(s == 'paid' ? 'Paid' : 'Unpaid'),
              subtitle: Text(s == 'paid' ? 'Customer has settled this order' : 'Awaiting payment'),
              tileColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: appBorder)),
            )).toList(),
          ),
        ),
        const SizedBox(height: 24),
        FilledButton(onPressed: _busy ? null : _save, child: Text(_busy ? 'Saving...' : 'Confirm')),
      ],
    ),
  );
}

/// Screen 104 — Invoices
class AgentInvoicesPage extends ConsumerStatefulWidget {
  const AgentInvoicesPage({super.key});

  @override
  ConsumerState<AgentInvoicesPage> createState() => _AgentInvoicesPageState();
}

class _AgentInvoicesPageState extends ConsumerState<AgentInvoicesPage> {
  late Future<List<Map<String, dynamic>>> _invoices;

  @override
  void initState() {
    super.initState();
    _invoices = ref.read(sourcingAgentBatchesRepositoryProvider).listInvoices();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'DOCUMENTS',
    title: 'Invoices',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _invoices,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load invoices.', actionLabel: 'Retry', onAction: () => setState(() => _invoices = ref.read(sourcingAgentBatchesRepositoryProvider).listInvoices()));
        }
        final items = snapshot.data ?? [];
        if (items.isEmpty) {
          return const CustomerEmptyState(icon: Icons.receipt_long_outlined, message: 'No invoices yet.');
        }
        return ListView.builder(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          itemCount: items.length,
          itemBuilder: (context, i) => _docCard(context, items[i], isInvoice: true),
        );
      },
    ),
  );
}

/// Screen 105 — Receipts
class AgentReceiptsPage extends ConsumerStatefulWidget {
  const AgentReceiptsPage({super.key});

  @override
  ConsumerState<AgentReceiptsPage> createState() => _AgentReceiptsPageState();
}

class _AgentReceiptsPageState extends ConsumerState<AgentReceiptsPage> {
  late Future<List<Map<String, dynamic>>> _receipts;

  @override
  void initState() {
    super.initState();
    _receipts = ref.read(sourcingAgentBatchesRepositoryProvider).listReceipts();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'DOCUMENTS',
    title: 'Receipts',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _receipts,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load receipts.', actionLabel: 'Retry', onAction: () => setState(() => _receipts = ref.read(sourcingAgentBatchesRepositoryProvider).listReceipts()));
        }
        final items = snapshot.data ?? [];
        if (items.isEmpty) {
          return const CustomerEmptyState(icon: Icons.receipt_outlined, message: 'No receipts yet.');
        }
        return ListView.builder(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          itemCount: items.length,
          itemBuilder: (context, i) => _docCard(context, items[i], isInvoice: false),
        );
      },
    ),
  );
}

Widget _docCard(BuildContext context, Map<String, dynamic> d, {required bool isInvoice}) {
  final num = d[isInvoice ? 'invoice_number' : 'receipt_number'] ?? '—';
  final amount = d['total_amount'] ?? 0;
  final currency = d['currency'] ?? 'TZS';
  final customer = d['customer_name'] ?? 'Guest';
  final batch = d['batch_title'];
  return InkWell(
    borderRadius: BorderRadius.circular(14),
    onTap: () => Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AgentDocumentDetailPage(document: d, isInvoice: isInvoice),
      ),
    ),
    child: Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(isInvoice ? Icons.description_outlined : Icons.receipt_long_outlined, color: isInvoice ? appError : appSuccess),
            const SizedBox(width: 10),
            Expanded(child: Text(num, style: const TextStyle(fontWeight: FontWeight.w800))),
            CustomerStatusPill(label: isInvoice ? (d['document_status'] ?? 'draft') : 'paid'),
          ]),
          const SizedBox(height: 8),
          Text('$customer', style: const TextStyle(color: appMuted, fontSize: 13)),
          if (batch != null) Text('Batch: $batch', style: const TextStyle(color: appMuted, fontSize: 12)),
          const SizedBox(height: 8),
          Text('$amount $currency', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: brandCoral)),
        ],
      ),
    ),
  );
}

/// Detail page for an invoice or receipt with view/download/share of the
/// backend-generated document.
class AgentDocumentDetailPage extends ConsumerStatefulWidget {
  const AgentDocumentDetailPage({
    required this.document,
    required this.isInvoice,
    super.key,
  });

  final Map<String, dynamic> document;
  final bool isInvoice;

  @override
  ConsumerState<AgentDocumentDetailPage> createState() =>
      _AgentDocumentDetailPageState();
}

class _AgentDocumentDetailPageState
    extends ConsumerState<AgentDocumentDetailPage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);

  bool _busy = false;
  String? _pdfUrl;

  @override
  void initState() {
    super.initState();
    _pdfUrl = widget.document['pdf_url'] as String?;
  }

  String get _docNumber =>
      widget.document[widget.isInvoice ? 'invoice_number' : 'receipt_number']
          as String? ??
      (widget.isInvoice ? 'Invoice' : 'Receipt');

  String get _fileName =>
      '${_docNumber.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_')}.pdf';

  Future<void> _ensurePdf() async {
    if (_pdfUrl != null && _pdfUrl!.isNotEmpty) return;
    final orderId = widget.document['order_id'] as String?;
    if (orderId == null) {
      throw 'Document PDF is not available.';
    }
    setState(() => _busy = true);
    try {
      final result = widget.isInvoice
          ? await _repository.generateInvoice(orderId)
          : await _repository.generateReceipt(orderId);
      if (!mounted) return;
      setState(() => _pdfUrl = result['pdf_url'] as String?);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _viewPdf() async {
    try {
      await _ensurePdf();
      final url = _pdfUrl;
      if (url == null || url.isEmpty) {
        throw 'No PDF available.';
      }
      setState(() => _busy = true);
      final bytes = await _repository.downloadPublicDocument(url);
      await DocumentHandler.saveAndOpen(bytes: bytes, fileName: _fileName);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to open the document.')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sharePdf() async {
    try {
      await _ensurePdf();
      final url = _pdfUrl;
      if (url == null || url.isEmpty) {
        throw 'No PDF available.';
      }
      setState(() => _busy = true);
      final bytes = await _repository.downloadPublicDocument(url);
      await DocumentHandler.saveAndShare(
        bytes: bytes,
        fileName: _fileName,
        subject: _docNumber,
        text: '${widget.isInvoice ? 'Invoice' : 'Receipt'}: $_docNumber',
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to share the document.')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.document;
    final amount = d['total_amount'] ?? 0;
    final currency = d['currency'] ?? 'TZS';
    final customer = d['customer_name'] ?? 'Guest';
    final status = d['document_status'] as String? ?? (widget.isInvoice ? 'draft' : 'paid');
    final generatedAt = d['generated_at'] as String?;
    final dueDate = d['due_date'] as String?;

    return Scaffold(
      appBar: SahajomyScreenHeader(
        role: 'Sourcing Agent',
        title: widget.isInvoice ? 'Invoice' : 'Receipt',
        actions: [
          IconButton(
            tooltip: 'Share',
            onPressed: _busy ? null : _sharePdf,
            icon: const Icon(Icons.share_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            _docNumber,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          CustomerStatusPill(label: status),
          const SizedBox(height: 20),
          _detailCard(
            entries: {
              'Customer': '$customer',
              'Amount': '$amount $currency',
              'Generated': ?generatedAt,
              'Due date': ?dueDate,
              if (d['batch_title'] != null) 'Batch': '${d['batch_title']}',
            },
          ),
          const SizedBox(height: 20),
          if (_pdfUrl == null || _pdfUrl!.isEmpty)
            FilledButton.icon(
              onPressed: _busy ? null : _viewPdf,
              icon: const Icon(Icons.picture_as_pdf_outlined),
              label: Text(_busy ? 'Generating…' : 'Generate & view PDF'),
            )
          else ...[
            FilledButton.icon(
              onPressed: _busy ? null : _viewPdf,
              icon: const Icon(Icons.visibility_outlined),
              label: const Text('View PDF'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : _sharePdf,
              icon: const Icon(Icons.share_outlined),
              label: const Text('Share PDF'),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _detailCard({required Map<String, String> entries}) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: appBorder),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final entry in entries.entries) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: Text(
                  entry.key,
                  style: const TextStyle(color: appMuted, fontSize: 13),
                ),
              ),
              Expanded(
                flex: 3,
                child: Text(
                  entry.value,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
            ],
          ),
          if (entry.key != entries.keys.last) const SizedBox(height: 10),
        ],
      ],
    ),
  );
}

/// Screen 178 — Share invoice
class AgentShareInvoicePage extends ConsumerStatefulWidget {
  const AgentShareInvoicePage({required this.orderId, required this.invoiceNumber, super.key});
  final String orderId;
  final String invoiceNumber;

  @override
  ConsumerState<AgentShareInvoicePage> createState() => _AgentShareInvoicePageState();
}

class _AgentShareInvoicePageState extends ConsumerState<AgentShareInvoicePage> {
  bool _busy = false;
  String? _result;

  Future<void> _share() async {
    setState(() => _busy = true);
    try {
      final res = await ref.read(sourcingAgentBatchesRepositoryProvider).shareInvoice(widget.orderId);
      setState(() => _result = res['message'] ?? 'Invoice shared');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'SHARE',
    title: 'Share invoice',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        CustomerHeroCard(eyebrow: widget.invoiceNumber, title: 'Share invoice with customer', subtitle: 'Send a notification with the invoice to the customer.'),
        const SizedBox(height: 20),
        if (_result != null)
          Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: appSuccess.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(14), border: Border.all(color: appSuccess)), child: Row(children: [const Icon(Icons.check_circle, color: appSuccess), const SizedBox(width: 8), Expanded(child: Text(_result!, style: const TextStyle(fontWeight: FontWeight.w700)))])),
        const SizedBox(height: 16),
        FilledButton.icon(onPressed: _busy ? null : _share, icon: const Icon(Icons.send_rounded), label: Text(_busy ? 'Sharing...' : 'Share invoice now')),
      ],
    ),
  );
}

/// Screen 109 — Available containers
class AgentAvailableContainersPage extends ConsumerStatefulWidget {
  const AgentAvailableContainersPage({super.key});

  @override
  ConsumerState<AgentAvailableContainersPage> createState() => _AgentAvailableContainersPageState();
}

class _AgentAvailableContainersPageState extends ConsumerState<AgentAvailableContainersPage> {
  late Future<List<Map<String, dynamic>>> _containers;

  @override
  void initState() {
    super.initState();
    _containers = ref.read(sourcingAgentBatchesRepositoryProvider).listAvailableContainers();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CONTAINERS',
    title: 'Available containers',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _containers,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load containers.', actionLabel: 'Retry', onAction: () => setState(() => _containers = ref.read(sourcingAgentBatchesRepositoryProvider).listAvailableContainers()));
        }
        final items = snapshot.data ?? [];
        if (items.isEmpty) {
          return const CustomerEmptyState(icon: Icons.local_shipping_outlined, message: 'No containers available right now.');
        }
        return ListView.builder(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          itemCount: items.length,
          itemBuilder: (context, i) {
            final c = items[i];
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    const Icon(Icons.inventory_2_outlined, color: brandNavy),
                    const SizedBox(width: 8),
                    Expanded(child: Text(c['container_size'] ?? 'Container', style: const TextStyle(fontWeight: FontWeight.w800))),
                    CustomerStatusPill(label: c['status'] ?? 'open'),
                  ]),
                  const SizedBox(height: 8),
                  Text(c['route'] ?? 'Route not assigned', style: const TextStyle(color: appMuted, fontSize: 13)),
                  Text('Operator: ${c['operator_name'] ?? 'Cargo Company'}', style: const TextStyle(color: appMuted, fontSize: 12)),
                  const SizedBox(height: 12),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: ((c['fill_percentage'] ?? 0) / 100).clamp(0.0, 1.0),
                      backgroundColor: appBorder,
                      valueColor: const AlwaysStoppedAnimation(brandCoral),
                      minHeight: 8,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(child: _metric('Available CBM', '${c['available_cbm']}')),
                      Expanded(child: _metric('Price / CBM', '${c['price_per_cbm']} ${c['currency'] ?? ''}')),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    ),
  );

  Widget _metric(String label, String value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
    ],
  );
}

/// Screen 110 — Book CBM
class AgentBookCbmPage extends ConsumerStatefulWidget {
  const AgentBookCbmPage({required this.container, super.key});
  final Map<String, dynamic> container;

  @override
  ConsumerState<AgentBookCbmPage> createState() => _AgentBookCbmPageState();
}

class _AgentBookCbmPageState extends ConsumerState<AgentBookCbmPage> {
  final _cbm = TextEditingController();
  final _city = TextEditingController();
  final _country = TextEditingController(text: 'Tanzania');
  final _formKey = GlobalKey<FormState>();
  bool _busy = false;

  @override
  void dispose() {
    _cbm.dispose(); _city.dispose(); _country.dispose();
    super.dispose();
  }

  Future<void> _book() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(sourcingAgentBatchesRepositoryProvider).bookCbm(
        containerId: '${widget.container['id']}',
        cbmAmount: double.parse(_cbm.text),
        destinationCity: _city.text.trim(),
        destinationCountry: _country.text.trim(),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('CBM booked successfully')));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final avail = widget.container['available_cbm'] ?? 0;
    final price = widget.container['price_per_cbm'] ?? 0;
    final currency = widget.container['currency'] ?? 'TZS';
    return CustomerScaffold(
      eyebrow: 'BOOK CBM',
      title: 'Book container space',
      notificationRoute: '/reference/agent-notifications',
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: widget.container['container_size'] ?? 'Container',
              title: 'Book CBM',
              subtitle: '${widget.container['route'] ?? ''} • $avail CBM available at $price $currency/CBM',
            ),
            const SizedBox(height: 16),
            TextFormField(controller: _cbm, decoration: InputDecoration(labelText: 'CBM amount (max $avail)', suffixText: 'CBM'), keyboardType: TextInputType.number, validator: (v) {
              final n = double.tryParse(v ?? '');
              if (n == null || n <= 0) return 'Enter a valid amount';
              if (n > avail) return 'Exceeds available CBM';
              return null;
            }),
            const SizedBox(height: 14),
            TextFormField(controller: _city, decoration: const InputDecoration(labelText: 'Destination city'), validator: (v) => v!.isEmpty ? 'Required' : null),
            const SizedBox(height: 14),
            TextFormField(controller: _country, decoration: const InputDecoration(labelText: 'Destination country')),
            const SizedBox(height: 24),
            FilledButton.icon(onPressed: _busy ? null : _book, icon: const Icon(Icons.check_circle_outline), label: Text(_busy ? 'Booking...' : 'Confirm booking')),
          ],
        ),
      ),
    );
  }
}

/// Screen 111 — Sea bookings.
class AgentSeaBookingsPage extends ConsumerStatefulWidget {
  const AgentSeaBookingsPage({super.key});

  @override
  ConsumerState<AgentSeaBookingsPage> createState() => _AgentSeaBookingsPageState();
}

class _AgentSeaBookingsPageState extends ConsumerState<AgentSeaBookingsPage> {
  late Future<List<Map<String, dynamic>>> _bookings;

  @override
  void initState() {
    super.initState();
    _bookings = ref.read(sourcingAgentBatchesRepositoryProvider).listSeaBookings();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'SEA BOOKINGS',
    title: 'My bookings',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _bookings,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load bookings.', actionLabel: 'Retry', onAction: () => setState(() => _bookings = ref.read(sourcingAgentBatchesRepositoryProvider).listSeaBookings()));
        }
        final items = snapshot.data ?? [];
        if (items.isEmpty) {
          return const CustomerEmptyState(icon: Icons.bookmark_border, message: 'No bookings yet.');
        }
        return ListView.builder(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          itemCount: items.length,
          itemBuilder: (context, i) {
            final b = items[i];
            final container = b['container'] as Map<String, dynamic>?;
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    const Icon(Icons.bookmark, color: brandCoral),
                    const SizedBox(width: 8),
                    Expanded(child: Text(b['booking_reference'] ?? 'Booking', style: const TextStyle(fontWeight: FontWeight.w800))),
                    CustomerStatusPill(label: b['payment_status'] ?? 'pending'),
                  ]),
                  const SizedBox(height: 6),
                  Text(container?['route'] ?? 'Container', style: const TextStyle(color: appMuted, fontSize: 13)),
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: _metric('CBM', '${b['cbm_booked']}')),
                    Expanded(child: _metric('Charge', '${b['logistics_charge']} ${b['currency'] ?? ''}')),
                    Expanded(child: _metric('Goods', b['goods_status'] ?? 'ready')),
                  ]),
                ],
              ),
            );
          },
        );
      },
    ),
  );

  Widget _metric(String label, String value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
    ],
  );
}
