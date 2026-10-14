---
type: Module
title: export-files
description: Dependency-free XLSX and PDF byte builders that turn a title plus header/data rows into a downloadable file for the tracker export.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/export_files.py
tags: [backend, export, xlsx, pdf]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T06:30:03Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 086ad0dd7cfe1a9581dd2f87de143759ef781634
    title: Codebase knowledge graph
status: stable
---

# Files

`app/services/export_files.py` — service-layer only; no router, schema, repository or model.

# Key symbols

| Symbol | Role |
|---|---|
| `build_file` | Entry point — dispatches on the wire format (`Excel`/`PDF`) and returns `bytes` |
| `build_xlsx` | Writes a minimal OOXML workbook (zip of `[Content_Types].xml`, `workbook.xml`, `sheet1.xml`) |
| `build_pdf` | Writes a minimal single-font PDF, paginating at `_PDF_LINES_PER_PAGE` |
| `CONTENT_TYPES` / `EXTENSIONS` | Wire format -> MIME type and file extension (`xlsx`, `pdf`) |
| `_xml_escape`, `_column_name`, `_pdf_escape` | Escaping/addressing helpers |

Both builders are written by hand against the file formats rather than pulling in a
spreadsheet or PDF package, per [Conventions](/conventions.md)' no-new-dependencies rule.

# Relationships

Called only by [Tracker](/modules/tracker.md)'s `app/services/tracker_export.py`
(`export_tracker_tab` to build the bytes, `get_export_file` to resolve the content type on
download). The bytes it returns are persisted through [Files](/modules/files.md).
