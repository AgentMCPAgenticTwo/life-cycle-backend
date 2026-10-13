"""Data access for the Cycle Time tab. Owns queries only -- the business rules (role
scoping, period/date-range resolution, per-stage/owner/contract-type grouping and averaging,
the empty-state tiers) live in `app.services.tracker_cycle_time`.

The entitlement, tenant-contract and user-name lookups are identical to the Bottleneck tab's
(UC10-BR-005/009/010/011 apply the same way here), so this module reuses
`app.repositories.tracker_bottleneck` for those rather than duplicating the queries; only the
completed-stage-history read is new.
"""
from app.repositories.tracker_bottleneck import (  # noqa: F401
    get_user_names,
    list_completed_stage_rows,
    list_owner_role_contract_ids,
    list_tenant_contracts,
)
