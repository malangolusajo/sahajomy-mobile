String normalizePhoneNumber(String value) {
  final trimmed = value.trim();
  final hasPlus = trimmed.startsWith('+');
  final digits = trimmed.replaceAll(RegExp(r'[^0-9]'), '');
  return '${hasPlus ? '+' : ''}$digits';
}

bool isValidPhoneNumber(String value) =>
    RegExp(r'^\+?[0-9]{7,15}$').hasMatch(normalizePhoneNumber(value));

bool isValidOtp(String value) => RegExp(r'^[0-9]{6}$').hasMatch(value);
