# Sahajomy Mobile Security Policy

Security reports should be sent privately to the Sahajomy security owner. Do
not open a public issue containing credentials, access links, customer data,
collection codes, PINs, or reproducible account-takeover steps.

## Client security baseline

- Release API traffic is HTTPS-only; Android cleartext traffic is disabled.
- Access/refresh tokens are held in platform secure storage and are removed on
  logout or definitive authentication failure.
- OTP phone numbers, MFA challenges, authenticator seeds, warehouse access
  links, collection codes, and PINs are memory-only.
- Privileged sessions fail closed unless `GET /auth/me` explicitly confirms MFA.
- Refresh is serialized and replayed once only. OTP, MFA, logout, payment,
  collection, QR rotation, intake, status, and handover actions are never
  automatically replayed.
- Tenant headers are centrally applied. A workspace change invalidates responses
  issued under the previous tenant revision before new data is rendered.
- Sensitive URI segments, headers, and request values are excluded from logs.
- Android screenshots, recordings, and recents thumbnails are blocked. iOS
  obscures the app while inactive.
- Android backup and device-transfer extraction are disabled for every storage
  domain.
- Only verified HTTPS app links are accepted; custom schemes are not registered.

## Release policy

Production release is blocked until every item in
`SECURITY_RELEASE_GATES.md` has current evidence and the repository security
workflow passes. Never commit `android/key.properties`, `*.jks`, `.env`, signing
passwords, API credentials, access tokens, or exported customer data.

Rotate any credential immediately if it is exposed. Revocation must happen on
the authoritative service; deleting it from Git history is not sufficient.
