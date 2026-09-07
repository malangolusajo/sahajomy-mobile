import 'package:flutter_riverpod/flutter_riverpod.dart';

final pendingOtpDeliveryProvider = StateProvider<OtpDelivery?>((ref) => null);

class OtpDelivery {
  const OtpDelivery({this.maskedEmail, this.expiresAt});
  final String? maskedEmail;
  final DateTime? expiresAt;
  factory OtpDelivery.fromJson(Map<String, dynamic> json) {
    final minutes = json['expires_in_minutes'];
    return OtpDelivery(
      maskedEmail: json['masked_email'] as String?,
      expiresAt: minutes is num && minutes > 0
          ? DateTime.now().add(Duration(seconds: (minutes * 60).round()))
          : null,
    );
  }
}
