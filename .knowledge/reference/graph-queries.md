---
type: Reference
title: graph-queries
description: How to query the live codebase-memory-mcp knowledge graph for the life-cycle-backend project instead of grepping source.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, reference, codebase-memory-mcp]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Project name

All calls use `project: "life-cycle-backend"`.

# Tools and when to use them

| Tool | Use for |
|---|---|
| `get_architecture` | Compact repo-wide facts: `aspects=["routes"]` for the route table, `["hotspots"]` for fan-in rankings, `["layers"]`/`["boundaries"]` for layering, `["clusters"]` for community detection, `["file_tree"]` for the directory tree. `path` scopes to a subdirectory. |
| `get_file_outline` | Declaration list (functions/classes/variables with line ranges) for one exact repo-relative file — the fastest way to see what a router/service/repository file exposes without reading it whole. |
| `search_graph` | Find a symbol by name/regex (`name_pattern`, `qn_pattern`) or by BM25/semantic query; returns qn/file/lines and in/out call edges. |
| `get_code_snippet` | Read the actual source of a `search_graph` result by qualified name; `source_mode: "outline"` for large containers, `"full"` for up to 500 lines. |
| `trace_path` | Caller/callee chains for a function name — e.g. who calls `require_roles`, or what `submit_action` calls into. |
| `query_graph` | Raw read-only Cypher for anything the above don't cover (multi-hop, aggregation). |

# Examples used while building this bundle

```
get_architecture(project="life-cycle-backend", aspects=["routes","layers","hotspots","boundaries"])
get_file_outline(project="life-cycle-backend", file_path="app/auth.py")
get_file_outline(project="life-cycle-backend", file_path="app/services/approvals.py")
get_architecture(project="life-cycle-backend", aspects=["clusters"])
```

# Tips

* `get_file_outline` needs the exact repo-relative path (e.g. `app/routers/contracts.py`), not a
  glob.
* `get_architecture(aspects=["hotspots"])` is the fastest way to find chokepoints like
  `app.auth.require_roles` (fan-in 93) before reading any source.
* Prefer `search_graph` + `get_code_snippet` over opening whole files when you only need one
  function's body — `get_code_snippet(source_mode="outline")` lists members first so you can
  pick a `start_line` instead of pulling the whole container.
* For "does X already exist elsewhere" questions (e.g. the seeding-convention check in
  [Conventions](/conventions.md)), a `search_graph(query="seed")` pass is faster and more
  complete than a manual grep across `app/` and `alembic/`.
