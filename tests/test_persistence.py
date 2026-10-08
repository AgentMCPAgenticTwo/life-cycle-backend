"""Foundation-layer guarantees: every table in the module contract has a matching ORM
entity, and the migration chain resolves to a single, correctly ordered line to `head`
without needing a live database (alembic's offline/`--sql` mode).
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

def test_every_contract_table_has_a_model():
    expected_tables = {t["name"] for t in CONTEXT["tables"]}
    assert expected_tables <= set(Base.metadata.tables.keys())


def test_model_columns_match_contract_columns():
    for table in CONTEXT["tables"]:
        model_table = Base.metadata.tables[table["name"]]
        model_columns = {c.name: c for c in model_table.columns}
        expected_columns = {c["name"] for c in table["columns"]}
        assert expected_columns == set(model_columns.keys()), table["name"]
        for col in table["columns"]:
            model_col = model_columns[col["name"]]
            assert model_col.nullable == col["nullable"], f"{table['name']}.{col['name']}"


def test_model_indexes_match_contract_indexes():
    for table in CONTEXT["tables"]:
        model_table = Base.metadata.tables[table["name"]]
        model_index_names = {idx.name for idx in model_table.indexes}
        expected_index_names = {idx["name"] for idx in table["indexes"]}
        assert expected_index_names == model_index_names, table["name"]


def test_migration_chain_matches_contract_order_exactly():
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    revisions = list(script.walk_revisions(base="base", head="head"))
    chain_oldest_first = [r.revision for r in reversed(revisions)]
    assert chain_oldest_first == CONTEXT["migrations"]


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
