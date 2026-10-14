# Correction a53cebba0be3

**Target:** backend

**Instruction:**

Context from the counterpart (frontend) correction: The frontend correction on ui-correction/e85937886fc6 introduced contract the backend does not yet integrate with: GET /api/v1/lifecycle/contracts/{contractId}/negotiation, POST /api/v1/lifecycle/contracts/{contractId}/negotiation/routing, GET /api/v1/lifecycle/contracts/{contractId}/negotiation/compare, GET /api/v1/lifecycle/contracts/{contractId}/clause-analysis, POST /api/v1/lifecycle/contracts/{contractId}/retry-extraction, GET /api/v1/templates, GET /api/v1/users, POST /api/v1/counterparties, POST /api/v1/contracts. Update the backend to call/consume these -- see this run's context_sharing for exact names and types -- following the existing code's patterns.

14. Contract Document Generation (UC2)
Works when: the user saves a contract with a template. Merge fields are filled in, and the document is created as Version 1.
If third-party paper is uploaded: that file becomes Version 1, with no merge.
Result: “Contract created successfully and saved as Draft”.
3. Re-check Risk After External Changes (UC5)
Re-analyses the clauses the counterparty changed.
Works when: the external party submits changes.
Result: only the changed clauses get a new risk score, and the overall score is updated.
If the AI fails: the version is still saved and the user can retry.

---

This branch was forked to isolate this one correction. sage-maintenance-agent's CI workflow commits its result on top of this note once it runs; see the PR's checks and commits for progress.
