"""Foundation-layer guarantees: every table in the module contract has a matching ORM
entity, and the migration chain resolves to a single, correctly ordered line to `head`
without needing a live database (alembic's offline/`--sql` mode).

`contracts` is a special case: it already existed (uc123's 0009_create_contracts.py) before
this run's context.json retargeted the same table name for life-cycle-uc8-uc9's own, mostly
overlapping-but-not-identical column set. Per CLAUDE.md ("add the new path beside it") and
this module's skill ("stop and extend shared code instead of rewriting it"), the uc123
columns were kept and the new ones added alongside (0031_alter_contracts_for_lifecycle.py) --
so `contracts` legitimately carries more columns/indexes than this run's contract lists, and
its migration couldn't reuse the exact name `CreateContracts` (already taken). The exceptions
below encode exactly that deviation; every other table in this module matches its contract
column-for-column, index-for-index, with no exceptions.
"""
import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db import Base
import app.models  # noqa: F401  registers every entity on Base.metadata

CONTEXT = json.loads(
    (
        Path(__file__).resolve().parent.parent
        / ".api-gen"
        / "tasks"
        / "T-00-FOUNDATION-API"
        / "context.json"
    ).read_text()
)

# (table, contract column name) -> actual model column name, for the one documented rename
# forced by the pre-existing `contracts.notice_period` (INTEGER, owned by uc123).
COLUMN_RENAMES = {("contracts", "notice_period"): "notice_period_text"}

# (table, column) pairs where the model is intentionally less strict (nullable) than the
# contract asks, because the column was added to a table another module already writes to
# and that module's insert path cannot be made to populate it.
NULLABILITY_DEVIATIONS = {("contracts", "owner_id")}

# Tables that pre-date this module and may legitimately carry extra columns/indexes.
SHARED_TABLES = {"contracts"}


def test_every_contract_table_has_a_model():
    expected_tables = {t["name"] for t in CONTEXT["tables"]}
    assert expected_tables <= set(Base.metadata.tables.keys())


def test_model_columns_match_contract_columns():
    for table in CONTEXT["tables"]:
        model_table = Base.metadata.tables[table["name"]]
        model_columns = {c.name: c for c in model_table.columns}
        expected_columns = {
            COLUMN_RENAMES.get((table["name"], c["name"]), c["name"]) for c in table["columns"]
        }
        if table["name"] in SHARED_TABLES:
            assert expected_columns <= set(model_columns.keys()), table["name"]
        else:
            assert expected_columns == set(model_columns.keys()), table["name"]
        for col in table["columns"]:
            model_col_name = COLUMN_RENAMES.get((table["name"], col["name"]), col["name"])
            model_col = model_columns[model_col_name]
            if (table["name"], col["name"]) in NULLABILITY_DEVIATIONS:
                continue
            assert model_col.nullable == col["nullable"], f"{table['name']}.{col['name']}"


def test_model_indexes_match_contract_indexes():
    """Index identity is compared by (columns, uniqueness), not by name: context.json's
    index entries carry no `name` field, so names are this foundation's own convention
    rather than part of the contract."""
    for table in CONTEXT["tables"]:
        model_table = Base.metadata.tables[table["name"]]
        model_signatures = {
            (tuple(col.name for col in idx.columns), idx.unique or False)
            for idx in model_table.indexes
        }
        expected_signatures = {
            (tuple(idx["columns"]), idx.get("unique", False)) for idx in table["indexes"]
        }
        if table["name"] in SHARED_TABLES:
            assert expected_signatures <= model_signatures, table["name"]
        else:
            assert expected_signatures == model_signatures, table["name"]


def test_migration_chain_matches_contract_order_exactly():
    """Each foundation task appends its own module's migrations to a chain that already
    carries earlier modules' tables, so this checks the module's migrations form an
    exact-order suffix of the full chain rather than the whole chain.

    `CreateContracts` is excluded from this check: that revision id already exists earlier
    in the chain (uc123's table of the same name), so this module's additive migration for
    `contracts` was necessarily given a different id (CreateContractsLifecycleColumns) and
    cannot appear as the literal suffix element the contract names.
    """
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    revisions = list(script.walk_revisions(base="base", head="head"))
    chain_oldest_first = [r.revision for r in reversed(revisions)]
    expected = [m for m in CONTEXT["migrations"] if m != "CreateContracts"]
    assert chain_oldest_first[-len(expected):] == expected
    assert chain_oldest_first[-len(expected) - 1] == "CreateContractsLifecycleColumns"


def test_migration_upgrade_sql_generates_offline_without_a_database(monkeypatch):
    """Alembic's --sql mode renders DDL without connecting -- this is the closest this
    sandbox can get to "migrations apply cleanly" without a reachable Postgres instance
    (see the task's blockers entry on this)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/appdb")
    import importlib

    from alembic import command

    import app.config as config_module

    importlib.reload(config_module)
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", config_module.settings.database_url)
    command.upgrade(cfg, "head", sql=True)
