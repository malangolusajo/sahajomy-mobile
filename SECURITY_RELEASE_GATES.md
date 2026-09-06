# Production Security Release Gates

The mobile client cannot prove or implement controls owned by the API, identity
provider, payment provider, DNS, CDN, Apple, or Google Play. A production build
must not ship until the release owner records evidence for every gate below.

## Identity and session

- OTP sending and verification are rate-limited per account, device, IP, and
  risk signal; responses do not reveal account existence.
- `POST /auth/mfa/setup` and `POST /auth/mfa/verify` use single-use, short-lived
  challenges. Authenticator seeds are returned only during setup.
- Every privileged `GET /auth/me` response includes `mfa_verified: true` (or
  `mfa_authenticated: true`) only after server-side MFA verification.
- Refresh tokens rotate on every use, reuse is detected, the token family is
  revoked on replay, and logout revokes the server session.
- Access tokens have short expiry, correct issuer/audience, strong signing, and
  no secrets or unnecessary personal data in claims.

## Authorisation and tenant isolation

- Every endpoint enforces role, company membership, branch scope, and granular
  permissions server-side. Client-provided tenant headers never grant access.
- Automated horizontal/vertical IDOR tests cover all resource IDs and roles.
- Workspace responses return a complete permissions list using the documented
  mobile capability names (`resource.read`, `resource.view`, `resource.manage`,
  `resource:*`, or `route:/path`).
- Logout and workspace switching invalidate tenant-scoped server caches and
  subscriptions.

## Capability links, warehouse and collection

- Warehouse/shared/receipt tokens use cryptographic randomness, have bounded
  TTL and scope, are revocable, are never logged, and are protected by a strict
  referrer policy on the website.
- Collection codes/PINs are short-lived, single-use, attempt-limited, bound to
  the selected paid parcels, and consumed atomically with physical handover.
- QR rotation, intake confirmation, readiness, payment, status changes, and
  handover accept idempotency keys but never rely on a client retry for safety.

## Uploads, payments and data handling

- Uploads are size-limited, MIME-sniffed, decoded/re-encoded, malware-scanned,
  stored outside executable paths, and served with safe content headers.
- Payment state is derived from signed provider webhooks and reconciled
  server-side; the mobile client cannot declare a payment successful.
- Logs, tracing, crash reporting, analytics, notifications, and support tooling
  redact tokens, OTPs, PINs, phone numbers, email addresses, labels, and parcel
  details. Access to production data is audited and least-privileged.

## Distribution and verified links

- `https://sahajomy.co.tz/.well-known/assetlinks.json` contains the production
  Android package and Play App Signing SHA-256 certificate fingerprint.
- `https://sahajomy.co.tz/.well-known/apple-app-site-association` contains the
  production Apple Team ID plus `com.sahajomy.mobile`, with only required paths.
- TLS, DNS, HSTS, certificate renewal, Apple/Google signing ownership, and store
  account MFA are verified before release.
- Run `tool/verify_release_security.ps1` with the production certificate and
  Apple Team ID; retain its successful output in the release record.

## Assurance

- Static analysis, tests, dependency vulnerability scanning, secret scanning,
  an API authorisation test suite, and a mobile/API penetration test pass for
  the release candidate.
- High/critical findings are fixed and retested. Accepted lower risks have an
  owner, expiry date, and written rationale.
