"""Business rules for the `lifecycle-uc4-uc5` module's AI Clause Analysis surface: risk
scoring (UC4-BR-001), mandatory-clause detection (UC4-BR-002, UC4-BR-017), accept/edit/reject
transitions (UC4-BR-014/015/018, UC4-AF-004), metadata relabelling (UC4-BR-007), the Ask AI
disclaimer (UC4-BR-008, UC4-AF-005), and the Proceed to Negotiation gate (UC4-BR-005,
UC4-AF-006). See CLAUDE.md's lifecycle-uc4-uc5 module section and this task's `blockers` for
the judgement calls this file makes where the contract or the AI pipeline itself is absent
from this sandbox.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models.clause import Clause as LibraryClause
from app.models.lifecycle_clause import AskAiInteraction, ClauseAuditLog, ContractClause, ContractMetadata
from app.repositories import contracts as contracts_repo
from app.repositories import lifecycle_clauses as repo
from app.schemas.lifecycle_clause import (
    AskAIRequest,
    AskAIResponse,
    AuditLogEntryResponse,
    ClauseAnalysisResponse,
    ClauseResponse,
    ContractMetadataResponse,
    EditClauseRequest,
    PagedAuditLogResponse,
    ProceedToNegotiationResponse,
    RejectClauseRequest,
    UpdateMetadataRequest,
)
from app.schemas.pagination import PageParams

_SUPPORTED_FORMATS = {"PDF", "DOCX"}
_RISK_RANK = {"Low": 1, "Medium": 2, "High": 3}
_DISCLAIMER = "AI suggestion only — verify before relying on this answer."
_MANDATORY_FLAG_LABEL = "Mandatory clause missing"
_MANDATORY_REJECT_MESSAGE = "This clause is mandatory and cannot be removed from the contract."

_METADATA_FIELD_MAP = {
    "parties": "parties_label",
    "contractValue": "contract_value_label",
    "startDate": "start_date_label",
    "endDate": "end_date_label",
    "renewalTerms": "renewal_terms_label",
    "paymentTerms": "payment_terms_label",
    "keyObligations": "key_obligations_label",
}
_METADATA_COLUMN_MAP = {
    "parties": "parties",
    "contractValue": "contract_value",
    "startDate": "start_date",
    "endDate": "end_date",
    "renewalTerms": "renewal_terms",
    "paymentTerms": "payment_terms",
    "keyObligations": "key_obligations",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_contract_or_404(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID):
    contract = contracts_repo.get_by_id(db, tenant_id, contract_id)
    if contract is None:
        raise NotFoundError("contract not found")
    return contract


def _file_format_supported(db: Session, tenant_id: uuid.UUID, contract) -> bool:
    """UC4-AF-001: the only document this module can inspect is the Third Party Paper
    upload -- a contract built from a Template has no uploaded document for this check, so
    it is treated as supported. See this task's `blockers`.
    """
    if contract.third_party_paper_file_id is None:
        return True
    uploaded = contracts_repo.get_uploaded_file(db, tenant_id, contract.third_party_paper_file_id)
    if uploaded is None:
        return True
    return uploaded.file_format.upper() in _SUPPORTED_FORMATS


def _overall_risk(clauses: list[ContractClause]) -> str:
    scored = [c for c in clauses if c.risk_score]
    if not scored:
        return "Low"
    best = max(scored, key=lambda c: _RISK_RANK.get(c.risk_score, 0))
    return best.risk_score


def _mandatory_flag(clause: ContractClause) -> bool:
    return bool(clause.is_mandatory and clause.library_match_status == "Missing" and not clause.mandatory_flag_cleared)


def _clause_to_response(clause: ContractClause) -> ClauseResponse:
    flag = _mandatory_flag(clause)
    return ClauseResponse(
        clauseId=clause.id,
        clauseText=clause.clause_text,
        clauseCategory=clause.clause_category,
        libraryMatchStatus=clause.library_match_status,
        riskScore=clause.risk_score,
        aiExplanation=clause.ai_explanation,
        suggestedText=clause.suggested_text,
        status=clause.status,
        isMandatory=clause.is_mandatory,
        mandatoryClauseFlag=flag,
        mandatoryClauseFlagLabel=_MANDATORY_FLAG_LABEL if flag else None,
        version=clause.version,
        updatedAt=clause.updated_at,
        updatedBy=clause.updated_by,
    )


def _metadata_to_response(metadata: ContractMetadata | None) -> ContractMetadataResponse | None:
    if metadata is None:
        return None
    return ContractMetadataResponse(
        parties=metadata.parties,
        partiesLabel=metadata.parties_label,
        contractValue=metadata.contract_value,
        contractValueLabel=metadata.contract_value_label,
        startDate=metadata.start_date,
        startDateLabel=metadata.start_date_label,
        endDate=metadata.end_date,
        endDateLabel=metadata.end_date_label,
        renewalTerms=metadata.renewal_terms,
        renewalTermsLabel=metadata.renewal_terms_label,
        paymentTerms=metadata.payment_terms,
        paymentTermsLabel=metadata.payment_terms_label,
        keyObligations=metadata.key_obligations,
        keyObligationsLabel=metadata.key_obligations_label,
    )


def _ensure_extraction(db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract) -> None:
    """Lazily materializes this contract's AI Clause Analysis state the first time it is
    opened. There is no real document-parsing/AI pipeline in this sandbox, so extraction is
    simulated: every mandatory, Active clause category in the tenant's clause library (UC123)
    that is not yet represented is seeded as Missing per UC4-BR-002, and a blank,
    'AI-suggested'-labelled metadata row is created per UC4-BR-007. See this task's
    `blockers`.
    """
    user_uuid = uuid.UUID(user.user_id) if user.user_id else contract.contract_owner_id
    now = _now()

    if repo.get_metadata(db, contract.id) is None:
        repo.insert_metadata(
            db,
            ContractMetadata(
                contract_id=contract.id,
                parties=None,
                parties_label="AI-suggested",
                contract_value=None,
                contract_value_label="AI-suggested",
                start_date=None,
                start_date_label="AI-suggested",
                end_date=None,
                end_date_label="AI-suggested",
                renewal_terms=None,
                renewal_terms_label="AI-suggested",
                payment_terms=None,
                payment_terms_label="AI-suggested",
                key_obligations=None,
                key_obligations_label="AI-suggested",
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )

    existing = repo.list_clauses(db, contract.id)
    existing_categories = {c.clause_category for c in existing if c.clause_category}
    mandatory_library_clauses = (
        db.query(LibraryClause)
        .filter(
            LibraryClause.tenant_id == tenant_id,
            LibraryClause.status == "Active",
            LibraryClause.mandatory.is_(True),
            LibraryClause.deleted_at.is_(None),
        )
        .all()
    )
    for lib_clause in mandatory_library_clauses:
        if lib_clause.clause_category in existing_categories:
            continue
        repo.insert_clause(
            db,
            ContractClause(
                contract_id=contract.id,
                clause_category=lib_clause.clause_category,
                library_match_status="Missing",
                risk_score="High",
                ai_explanation=None,
                suggested_text=None,
                clause_text="",
                status="AI-Suggested",
                is_mandatory=True,
                mandatory_flag_cleared=False,
                version=1,
                created_at=now,
                created_by=user_uuid,
                updated_at=now,
                updated_by=user_uuid,
            ),
        )
    db.commit()


def _blocked_response(contract_id: uuid.UUID) -> ClauseAnalysisResponse:
    return ClauseAnalysisResponse(
        contractId=contract_id,
        fileFormatSupported=False,
        analysisStatus="Blocked",
        clauses=[],
        overallContractRiskScore="Low",
        metadata=None,
        proceedToNegotiationEnabled=False,
        askAiEnabled=False,
    )


def _build_analysis_response(db: Session, user: CurrentUser, contract) -> ClauseAnalysisResponse:
    clauses = repo.list_clauses(db, contract.id)
    metadata = repo.get_metadata(db, contract.id)
    overall = _overall_risk(clauses)
    any_missing_mandatory = any(_mandatory_flag(c) for c in clauses)
    # UC5: a re-analysis that failed after an external redline leaves the contract reporting
    # 'Failed' until a retry succeeds -- the version itself is already saved either way.
    failed = pending_reanalysis_failure(db, contract.id) is not None
    return ClauseAnalysisResponse(
        contractId=contract.id,
        fileFormatSupported=True,
        analysisStatus="Failed" if failed else "Completed",
        clauses=[_clause_to_response(c) for c in clauses],
        overallContractRiskScore=overall,
        metadata=_metadata_to_response(metadata),
        proceedToNegotiationEnabled=not any_missing_mandatory and not failed,
        askAiEnabled=user.role != "TENANT_ADMIN",
    )


def get_clause_analysis(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> ClauseAnalysisResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    if not _file_format_supported(db, tenant_id, contract):
        return _blocked_response(contract.id)
    _ensure_extraction(db, tenant_id, user, contract)
    return _build_analysis_response(db, user, contract)


def retry_extraction(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> ClauseAnalysisResponse:
    # UC4-AF-002: re-attempt extraction -- idempotent with the initial extraction (see
    # `_ensure_extraction`). UC5: when the outstanding failure is a re-analysis of the
    # clauses a counterparty changed, retry re-scores exactly those clauses again.
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    failure = pending_reanalysis_failure(db, contract.id)
    if failure is not None:
        user_uuid = uuid.UUID(user.user_id) if user.user_id else contract.contract_owner_id
        reanalyze_clauses(db, contract.id, user_uuid, _clause_ids_from_failure(failure))
    return get_clause_analysis(db, tenant_id, user, contract_id)


def _get_clause_or_404(db: Session, contract_id: uuid.UUID, clause_id: uuid.UUID) -> ContractClause:
    clause = repo.get_clause(db, contract_id, clause_id)
    if clause is None:
        raise NotFoundError("clause not found")
    return clause


def _write_audit(
    db: Session,
    *,
    contract_id: uuid.UUID,
    clause_id: uuid.UUID | None,
    user_id: uuid.UUID,
    action_type: str,
    field_name: str | None,
    before_text: str | None,
    after_text: str | None,
    now: datetime,
) -> None:
    repo.insert_audit_entry(
        db,
        ClauseAuditLog(
            contract_id=contract_id,
            clause_id=clause_id,
            user_id=user_id,
            action_type=action_type,
            field_name=field_name,
            before_text=before_text,
            after_text=after_text,
            occurred_at=now,
            created_at=now,
            created_by=user_id,
            updated_at=now,
            updated_by=user_id,
        ),
    )


def accept_suggestion(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, clause_id: uuid.UUID
) -> ClauseResponse:
    _get_contract_or_404(db, tenant_id, contract_id)
    clause = _get_clause_or_404(db, contract_id, clause_id)

    # UC4-BR-014: only an AI-Suggested clause with suggested text can be accepted in one
    # click; UC4-BR-017: a Missing-Mandatory clause has no suggested text to accept.
    if clause.status != "AI-Suggested" or not clause.suggested_text:
        raise ConflictError("This clause suggestion is no longer available to accept.")

    before_text = clause.clause_text
    user_uuid = uuid.UUID(user.user_id)
    now = _now()
    clause.clause_text = clause.suggested_text
    clause.status = "Accepted"
    clause.version += 1
    clause.updated_at = now
    clause.updated_by = user_uuid

    _write_audit(
        db,
        contract_id=contract_id,
        clause_id=clause.id,
        user_id=user_uuid,
        action_type="Accept",
        field_name="clauseText",
        before_text=before_text,
        after_text=clause.clause_text,
        now=now,
    )
    db.commit()
    db.refresh(clause)
    return _clause_to_response(clause)


def edit_clause(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    clause_id: uuid.UUID,
    payload: EditClauseRequest,
) -> ClauseResponse:
    _get_contract_or_404(db, tenant_id, contract_id)
    clause = _get_clause_or_404(db, contract_id, clause_id)

    # UC4-AF-004: optimistic concurrency -- a stale `expectedVersion` blocks the save instead
    # of silently overwriting a concurrent edit.
    if payload.expectedVersion != clause.version:
        raise ConflictError("This clause was just updated by another user. Please refresh to see the latest version.")

    if not payload.clauseText.strip():
        raise ValidationFailedError("Clause text is required.", details=["Clause text is required."])

    before_text = clause.clause_text
    user_uuid = uuid.UUID(user.user_id)
    now = _now()
    clause.clause_text = payload.clauseText
    clause.status = "Edited (Manual)"
    # UC4-BR-005/BR-017: replacing a Missing clause's text resolves the Missing status and
    # clears the Mandatory Clause Flag.
    if clause.library_match_status == "Missing":
        clause.library_match_status = "Standard"
        clause.mandatory_flag_cleared = True
    clause.version += 1
    clause.updated_at = now
    clause.updated_by = user_uuid

    _write_audit(
        db,
        contract_id=contract_id,
        clause_id=clause.id,
        user_id=user_uuid,
        action_type="Edit",
        field_name="clauseText",
        before_text=before_text,
        after_text=clause.clause_text,
        now=now,
    )
    db.commit()
    db.refresh(clause)
    return _clause_to_response(clause)


def reject_clause(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    clause_id: uuid.UUID,
    payload: RejectClauseRequest,
) -> ClauseResponse:
    _get_contract_or_404(db, tenant_id, contract_id)
    clause = _get_clause_or_404(db, contract_id, clause_id)

    # UC3: a mandatory clause can never be rejected out of the contract. The UI hides the
    # control, but the rule has to hold here too -- the API is reachable without it.
    if clause.is_mandatory:
        raise ConflictError(
            _MANDATORY_REJECT_MESSAGE, details=[_MANDATORY_REJECT_MESSAGE]
        )

    before_status = clause.status
    user_uuid = uuid.UUID(user.user_id)
    now = _now()
    clause.status = "Rejected"
    clause.version += 1
    clause.updated_at = now
    clause.updated_by = user_uuid

    _write_audit(
        db,
        contract_id=contract_id,
        clause_id=clause.id,
        user_id=user_uuid,
        action_type="Reject",
        field_name="status",
        before_text=before_status,
        after_text=clause.status,
        now=now,
    )
    db.commit()
    db.refresh(clause)
    return _clause_to_response(clause)


def update_metadata(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    payload: UpdateMetadataRequest,
) -> ContractMetadataResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    metadata = repo.get_metadata(db, contract.id)
    user_uuid = uuid.UUID(user.user_id)
    now = _now()
    if metadata is None:
        metadata = repo.insert_metadata(
            db,
            ContractMetadata(
                contract_id=contract.id,
                parties_label="AI-suggested",
                contract_value_label="AI-suggested",
                start_date_label="AI-suggested",
                end_date_label="AI-suggested",
                renewal_terms_label="AI-suggested",
                payment_terms_label="AI-suggested",
                key_obligations_label="AI-suggested",
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )

    provided = payload.model_dump(exclude_unset=True)
    for field_name, column_name in _METADATA_COLUMN_MAP.items():
        if field_name not in provided:
            continue
        new_value = provided[field_name]
        if field_name == "contractValue" and new_value is not None:
            new_value = Decimal(str(new_value))
        old_value = getattr(metadata, column_name)
        if old_value == new_value:
            continue
        setattr(metadata, column_name, new_value)
        setattr(metadata, _METADATA_FIELD_MAP[field_name], "User-confirmed")
        # UC4-BR-006: every metadata change is logged with before/after text.
        _write_audit(
            db,
            contract_id=contract.id,
            clause_id=None,
            user_id=user_uuid,
            action_type="MetadataUpdate",
            field_name=field_name,
            before_text=str(old_value) if old_value is not None else None,
            after_text=str(new_value) if new_value is not None else None,
            now=now,
        )

    metadata.updated_at = now
    metadata.updated_by = user_uuid
    db.commit()
    db.refresh(metadata)
    return _metadata_to_response(metadata)


def ask_ai(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, payload: AskAIRequest
) -> AskAIResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)

    # UC4-AF-005: an empty question never reaches the AI.
    if not payload.question or not payload.question.strip():
        raise ValidationFailedError(
            "Please enter a question before submitting.", details=["Please enter a question before submitting."]
        )

    metadata = repo.get_metadata(db, contract.id)
    if metadata is None:
        raise ConflictError("AI analysis is not available for this contract.")

    clauses = repo.list_clauses(db, contract.id)
    user_uuid = uuid.UUID(user.user_id)
    now = _now()

    # No real AI/LLM call is available in this sandbox -- the answer is a templated summary
    # of the current clause analysis state, always carrying the disclaimer. See `blockers`.
    overall = _overall_risk(clauses)
    answer = (
        f"Based on the current clause analysis (overall risk: {overall}), "
        f"here is the available information relevant to your question: \"{payload.question.strip()}\"."
    )
    related_ids = [c.id for c in clauses]

    repo.insert_ask_ai_interaction(
        db,
        AskAiInteraction(
            contract_id=contract.id,
            user_id=user_uuid,
            question=payload.question,
            answer=answer,
            disclaimer=_DISCLAIMER,
            related_clause_ids=[str(i) for i in related_ids],
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    db.commit()
    return AskAIResponse(answer=answer, disclaimer=_DISCLAIMER, relatedClauseIds=related_ids)


def proceed_to_negotiation(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> ProceedToNegotiationResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    clauses = repo.list_clauses(db, contract.id)
    metadata = repo.get_metadata(db, contract.id)

    # UC4-BR-005/AF-006: any clause still flagged Missing-Mandatory blocks the transition.
    if any(_mandatory_flag(c) for c in clauses):
        raise ConflictError(
            "This contract is missing one or more mandatory clauses. Resolve all red-flagged clauses before proceeding."
        )

    # UC4-BR-013: this screen never moves the contract's own (UC2) Draft status -- UC5's
    # routing endpoint is the only thing that advances negotiation.
    return ProceedToNegotiationResponse(
        contractId=contract.id,
        negotiationStatus="Ready for Negotiation",
        routedAt=None,
        clauses=[_clause_to_response(c) for c in clauses],
        overallContractRiskScore=_overall_risk(clauses),
        metadata=_metadata_to_response(metadata),
        askAiAvailable=True,
    )


def has_completed_analysis_pass(db: Session, contract_id: uuid.UUID) -> bool:
    """UC5-BR-023: routing may only be triggered once this contract has at least one
    completed AI Clause Analysis pass (UC4) -- a `contract_metadata` row is only ever created
    by `_ensure_extraction`, so its presence is proof a pass has run.
    """
    return repo.get_metadata(db, contract_id) is not None


def has_unresolved_mandatory_clauses(db: Session, contract_id: uuid.UUID) -> bool:
    return any(_mandatory_flag(c) for c in repo.list_clauses(db, contract_id))


def get_overall_risk(db: Session, contract_id: uuid.UUID) -> str:
    return _overall_risk(repo.list_clauses(db, contract_id))


def snapshot_clauses(db: Session, contract_id: uuid.UUID) -> list[dict]:
    """A plain-dict snapshot of the current clause set, used by negotiation versioning
    (`negotiation_versions.document_snapshot`) to support Compare Versions redlines."""
    return [
        {"clauseId": str(c.id), "clauseCategory": c.clause_category, "clauseText": c.clause_text}
        for c in repo.list_clauses(db, contract_id)
    ]


# --- UC5: risk re-check after external changes ----------------------------------------
# No real AI pipeline exists in this sandbox, so re-scoring is a deterministic keyword pass
# over the clause text. What matters for UC5 is the surrounding behaviour: only the clauses
# the counterparty actually changed are re-scored, the overall contract score follows from
# them, and a failure leaves the saved version intact with a retryable 'Failed' status.

_HIGH_RISK_TERMS = (
    "unlimited liability",
    "indemnif",
    "uncapped",
    "terminate at will",
    "sole discretion",
    "no liability cap",
    "waive",
)
_MEDIUM_RISK_TERMS = (
    "may terminate",
    "best efforts",
    "reasonable",
    "penalty",
    "late fee",
    "renew automatically",
)


def _score_clause_text(text: str) -> tuple[str, str]:
    lowered = (text or "").lower()
    hit = next((term for term in _HIGH_RISK_TERMS if term in lowered), None)
    if hit is not None:
        return "High", f"Re-scored after counterparty changes: the revised text introduces '{hit}'."
    hit = next((term for term in _MEDIUM_RISK_TERMS if term in lowered), None)
    if hit is not None:
        return "Medium", f"Re-scored after counterparty changes: the revised text contains '{hit}'."
    return "Low", "Re-scored after counterparty changes: no elevated-risk language detected."


def apply_external_redlines(
    db: Session,
    contract_id: uuid.UUID,
    user_id: uuid.UUID,
    redlines: list[tuple[uuid.UUID, str]],
    redline_text: str | None,
) -> list[uuid.UUID]:
    """Applies a counterparty's submission to this contract's clauses and returns the ids of
    the clauses it changed -- the input to the UC5 re-check.

    Two shapes are accepted. A structured submission (`clauseId`/`clauseText` pairs) replaces
    the named clauses' text. A plain redline document, which is all the external submit
    contract guarantees, cannot say which clause is which, so a clause counts as changed when
    its current text no longer appears verbatim in the returned document.
    """
    now = _now()
    changed: list[uuid.UUID] = []

    if redlines:
        for clause_id, new_text in redlines:
            clause = repo.get_clause(db, contract_id, clause_id)
            if clause is None or clause.clause_text == new_text:
                continue
            before = clause.clause_text
            clause.clause_text = new_text
            clause.version += 1
            clause.updated_at = now
            clause.updated_by = user_id
            _write_audit(
                db,
                contract_id=contract_id,
                clause_id=clause.id,
                user_id=user_id,
                action_type="External Redline",
                field_name="clauseText",
                before_text=before,
                after_text=new_text,
                now=now,
            )
            changed.append(clause.id)
        return changed

    document = (redline_text or "").strip()
    if not document:
        return changed
    for clause in repo.list_clauses(db, contract_id):
        if clause.clause_text and clause.clause_text.strip() not in document:
            changed.append(clause.id)
    return changed


_REANALYSIS_ACTION = "Re-analysis"
_REANALYSIS_FAILED_ACTION = "Re-analysis Failed"
_ANALYSIS_STATUS_FIELD = "analysisStatus"


def pending_reanalysis_failure(db: Session, contract_id: uuid.UUID) -> ClauseAuditLog | None:
    """The outstanding re-analysis failure for this contract, if the most recent re-analysis
    attempt failed and has not since been retried successfully."""
    entry = repo.get_latest_audit_entry(
        db,
        contract_id,
        action_types=[_REANALYSIS_ACTION, _REANALYSIS_FAILED_ACTION],
        field_name=_ANALYSIS_STATUS_FIELD,
    )
    if entry is not None and entry.action_type == _REANALYSIS_FAILED_ACTION:
        return entry
    return None


def _clause_ids_from_failure(entry: ClauseAuditLog) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for raw in (entry.after_text or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            ids.append(uuid.UUID(raw))
        except ValueError:
            continue
    return ids


def _record_reanalysis_failure(
    db: Session, contract_id: uuid.UUID, user_id: uuid.UUID, clause_ids: list[uuid.UUID]
) -> None:
    now = _now()
    _write_audit(
        db,
        contract_id=contract_id,
        clause_id=None,
        user_id=user_id,
        action_type=_REANALYSIS_FAILED_ACTION,
        field_name=_ANALYSIS_STATUS_FIELD,
        before_text=None,
        # The clauses still awaiting a score, so Retry re-analyses exactly those.
        after_text=",".join(str(cid) for cid in clause_ids),
        now=now,
    )
    db.commit()


def reanalyze_clauses(
    db: Session, contract_id: uuid.UUID, user_id: uuid.UUID, clause_ids: list[uuid.UUID]
) -> bool:
    """Re-scores the given clauses and records the outcome. Returns False when the pass
    failed -- the caller's already-saved version stays saved and the contract reports
    `analysisStatus: 'Failed'` until a retry succeeds."""
    if not clause_ids:
        return True
    try:
        now = _now()
        for clause_id in clause_ids:
            clause = repo.get_clause(db, contract_id, clause_id)
            if clause is None:
                continue
            before = clause.risk_score
            risk, explanation = _score_clause_text(clause.clause_text)
            clause.risk_score = risk
            clause.ai_explanation = explanation
            clause.updated_at = now
            clause.updated_by = user_id
            _write_audit(
                db,
                contract_id=contract_id,
                clause_id=clause.id,
                user_id=user_id,
                action_type=_REANALYSIS_ACTION,
                field_name="riskScore",
                before_text=before,
                after_text=risk,
                now=now,
            )
        _write_audit(
            db,
            contract_id=contract_id,
            clause_id=None,
            user_id=user_id,
            action_type=_REANALYSIS_ACTION,
            field_name=_ANALYSIS_STATUS_FIELD,
            before_text=None,
            after_text="Completed",
            now=now,
        )
        db.commit()
        return True
    except Exception:  # noqa: BLE001 -- UC5: any AI failure must not lose the saved version
        db.rollback()
        _record_reanalysis_failure(db, contract_id, user_id, clause_ids)
        return False


def get_audit_log(
    db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID, page_params: PageParams
) -> PagedAuditLogResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    rows, total = repo.list_audit_log(
        db, contract.id, offset=page_params.offset, limit=page_params.page_size
    )
    items = []
    for row in rows:
        user_row = contracts_repo.get_user(db, tenant_id, row.user_id)
        items.append(
            AuditLogEntryResponse(
                id=row.id,
                userId=row.user_id,
                userName=user_row.name if user_row is not None else "Unknown",
                timestamp=row.occurred_at,
                clauseId=row.clause_id,
                actionType=row.action_type,
                fieldName=row.field_name,
                beforeText=row.before_text,
                afterText=row.after_text,
            )
        )
    return PagedAuditLogResponse(
        items=items, page=page_params.page, pageSize=page_params.page_size, totalCount=total
    )
