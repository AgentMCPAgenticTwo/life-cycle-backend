# Correction 6ad9e7fe97fb

**Target:** backend

**Instruction:**

Context from the counterpart (frontend) correction: The frontend correction on ui-correction/8eaf9ad68d6a introduced contract the backend does not yet integrate with: POST /auth/refresh, POST /auth/login, POST /auth/logout, GET /auth/me, POST /auth/change-password. Update the backend to call/consume these -- see this run's context_sharing for exact names and types -- following the existing code's patterns.

Fix the refresh token flow in the existing project. The access token works, but refresh token functionality is not working. Identify and fix the root cause, implement automatic access token renewal when it expires, and verify the complete authentication flow without breaking existing functionality.

---

This branch was forked to isolate this one correction. sage-maintenance-agent's CI workflow commits its result on top of this note once it runs; see the PR's checks and commits for progress.
