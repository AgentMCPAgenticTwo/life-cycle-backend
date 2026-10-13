"""Data access for the Ownership tab. Owns queries only -- the business rules (role scoping,
stage derivation, per-owner aggregation, the empty-state tiers) live in
`app.services.tracker_ownership`.

The entitlement, open-stage, tenant-contract, threshold-free and user-name lookups are
identical to the Bottleneck tab's (UC10-BR-005/009/010/011 apply the same way here), so this
module reuses `app.repositories.tracker_bottleneck` for those rather than duplicating the
queries; only the completed-stage-history read (reused for the per-owner average cycle time)
is new here too, but it already lives on that same module.
"""
from app.repositories.tracker_bottleneck import (  # noqa: F401
    STATUS_TO_STAGE,
    get_user_names,
    list_completed_stage_rows,
    list_open_stage_rows,
    list_owner_role_contract_ids,
    list_tenant_contracts,
)
