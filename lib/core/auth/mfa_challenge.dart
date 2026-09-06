/// Deliberately memory-only. Never persist or place this material in a URL.
class MfaChallenge {
  const MfaChallenge({
    required this.challengeToken,
    this.setupRequired = false,
    this.otpAuthUri,
    this.manualSecret,
  });

  final String challengeToken;
  final bool setupRequired;
  final String? otpAuthUri;
  final String? manualSecret;

  MfaChallenge copyWith({String? otpAuthUri, String? manualSecret}) =>
      MfaChallenge(
        challengeToken: challengeToken,
        setupRequired: setupRequired,
        otpAuthUri: otpAuthUri ?? this.otpAuthUri,
        manualSecret: manualSecret ?? this.manualSecret,
      );
}
