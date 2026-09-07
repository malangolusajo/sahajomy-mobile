# Approved core screens: contract audit

The Flutter application is at the repository root (`pubspec.yaml`, `lib/`). The nested Sahajomy-Mobile-App folder is the supplied handoff/reference package. Contracts below were checked against D:/Projects/sahajomy-platform/backend/app on 2026-09-07; the backend-app-folder remains an additional reference. No backend files are changed.

## Mapping before implementation

| Screen / role | Purpose and API / request | Response and navigation | States |
| --- | --- | --- | --- |
| 001 Splash / shared | Read secure session and onboarding preference; GET auth/me with refresh interceptor for existing sessions | Verified role; enter checking-workspace or onboarding/sign-in | Startup indicator; retry on offline/server error; reject invalid session |
| 006 Welcome / shared | POST auth/send-otp {phone_number} | masked_email, expires_in_minutes; OTP page. Exact new-registration error routes to registration with entered phone | Form validation, busy, backend error, retry; no list/empty state |
| 007 Create account / shared | POST auth/send-otp {phone_number,name,email} | masked_email, expires_in_minutes; OTP page | Retain fields on error, disable duplicate submit; email errors from server |
| 008 Verify code / shared | POST auth/verify-otp {phone_number,otp_code}; GET auth/me; existing MFA step retained | Secure tokens, verified role; notification permission then workspace check; pending deep link retained | Invalid code inline; expiry from server duration/410; resend uses send-otp; rate-limit error; busy |
| 009 Code expired / shared | Recovery from actual OTP expiry; send-otp on request-new-code | New challenge returns to verification | Resend busy/error; change-number recovery; no fabricated reference |
| 010 Account suspended / shared | Actual suspended error (backend can return 400 from OTP service or 403 from auth); official support link | Contact support or return to sign-in | Launch failure fallback; no fabricated support case |
| 011 Stay updated / authenticated shared | Native OS notification permission request | Allowed/denied/unavailable; continue to workspace check | Busy, denied explanation, retry/settings, optional skip |
| 012 Switch workspace / authenticated shared | GET workspaces (no tenant header) | personal object, companies list: id,type,company_id,company_name,branch_id,branch_name,role,status,permissions | Loading, refresh, retry, personal-only; select then Continue; clear old tenant before saving |
| 013 Choose branch / company members | GET workspaces/branches only with company.branch.manage; GET workspaces/roles validates selected tenant scope | id,name,city,country,company_id; persist authorized branch, then checking screen | Loading/error/empty/retry; members without permission keep backend default branch |
| 014 Checking workspace / authenticated shared | GET auth/me + GET workspaces; selected company GET workspaces/roles checks membership/branch headers | Refresh membership permissions and select role shell or pbooked deep link | Indeterminate progress (no invented percentage); offline/retry; removed membership clears selection and returns picker |

## Existing implementation reused

Riverpod providers; AuthRepository and ApiClient; SessionStore and secure TokenStorage; refresh/auth/tenant interceptors; GoRouter and app-link guard; original SVG logo. Existing auth/MFA behavior remains authoritative. Equivalent core layouts are consolidated rather than duplicated per screen.

## Discrepancies

- The brief forbids the screenshot's generic SAHAJOMY app-bar eyebrow: headers use contextual titles only.
- The original logo is used unchanged; separate splash brand text is removed per the user's explicit request.
- Workspaces are `{personal, companies}`, not the old Flutter `{workspaces}` assumption. Account role is not changed by selecting a company membership. The server remains authoritative for role-only operational endpoints.
- Branch listing requires company.branch.manage. A non-manager can retain the assigned default branch but cannot browse arbitrary branches. The screenshot's three locations are example data.
- Screenshot reference SAH-260907-4829 is not supplied by auth: no claim that a reference was saved to an account.
- OTP delivery is email; response supplies expiry duration. Resend cooldown is a client affordance; backend rate limits remain authoritative.
- There is no push-device registration endpoint in the inspected notification routes. OS permission is real; remote push delivery still requires a supported backend/device-token integration. In-app notification endpoints remain intact.
- No unread badge is fabricated on unauthenticated headers. No dropdown chevrons are added to free-text name/email fields.

## Validation

Pending implementation and test results.
