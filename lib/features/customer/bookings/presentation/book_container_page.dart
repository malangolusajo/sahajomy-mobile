import 'package:flutter/material.dart';

import '../../../booking/data/guided_booking_repository.dart';
import '../../../booking/presentation/guided_sea_booking_page.dart';

class BookContainerPage extends StatelessWidget {
  const BookContainerPage({required this.container, super.key});
  final Map<String, dynamic> container;
  @override
  Widget build(BuildContext context) => GuidedSeaBookingPage(
    account: BookingAccount.customer,
    initialContainerId: '${container['id']}',
  );
}
