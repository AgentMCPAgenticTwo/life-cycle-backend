# Correction 92a2ebacae78

**Target:** backend

**Instruction:**

Context from the counterpart (frontend) correction: The frontend correction on ui-correction/7ac3665310c8 introduced contract the backend does not yet integrate with: GET /api/v1/signing-sessions/{sessionId}, POST /api/v1/signing-sessions/{sessionId}/otp/verify, POST /api/v1/signing-sessions/{sessionId}/otp/resend, POST /api/v1/signing-sessions/{sessionId}/sign, POST /api/v1/signing-sessions/{sessionId}/decline. Update the backend to call/consume these -- see this run's context_sharing for exact names and types -- following the existing code's patterns.

Sign → Executed
In the backend terminal, find the email to anita.signer@demo.local. Copy the signing link and OTP.
Sign out and log in as anita.signer@demo.local.
Open the link (localhost:5173/sign/<sessionId>).
Enter the OTP and click Verify.
Choose Type, enter Anita Rao, and click Sign.
in this flow You have been asked to sign NDA - Kaveri Exports Pvt Ltd. Open your signing link and enter the one-time password sent to you to continue. in mail this only for singer link generate  i need like this for contract company we send link i like below 
Internal review of NDA - Kaveri Exports Pvt Ltd is complete and the contract has been sent to you for review.
Secure link reference: hQSA4AS1cPZfHN-dxvIDMukDQfhfeIuQ
One-time password: 543687
The link expires at 2026-10-18 10:01 UTC.
for signed flow missing otp and link clcik to open fix it

---

This branch was forked to isolate this one correction. sage-maintenance-agent's CI workflow commits its result on top of this note once it runs; see the PR's checks and commits for progress.
