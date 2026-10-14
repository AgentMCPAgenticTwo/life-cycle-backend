"""Real export-file bytes for `POST /api/v1/tracker/export` (UC10): a tabular snapshot of
the tab the user is looking at, for the period and filters they have applied.

CLAUDE.md forbids adding packages, so both writers are hand-rolled on the standard library:
`.xlsx` is a zip of SpreadsheetML parts (`zipfile`), `.pdf` is a hand-written PDF 1.4 file
with a Helvetica text stream. Both are real, openable files -- not placeholders.
"""
import zipfile
from io import BytesIO

_XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_CONTENT_TYPE = "application/pdf"

CONTENT_TYPES = {"Excel": _XLSX_CONTENT_TYPE, "PDF": _PDF_CONTENT_TYPE}
EXTENSIONS = {"Excel": "xlsx", "PDF": "pdf"}


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _column_name(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def build_xlsx(sheet_name: str, headers: list[str], rows: list[list[str]]) -> bytes:
    """A single-sheet workbook with every cell written as an inline string -- no shared
    string table to keep the part set minimal."""
    sheet_rows = []
    for row_index, row in enumerate([headers, *rows], start=1):
        cells = []
        for column_index, value in enumerate(row):
            reference = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">'
                f"{_xml_escape(value)}</t></is></c>"
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{_xml_escape(sheet_name[:31])}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.spreadsheetml.worksheet+xml"/></Types>'
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def _pdf_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # The base-14 Helvetica encoding is single-byte; drop anything outside it rather than
    # emitting bytes a reader would render as mojibake.
    return escaped.encode("latin-1", "replace").decode("latin-1")


_PDF_LINES_PER_PAGE = 45


def build_pdf(title: str, headers: list[str], rows: list[list[str]]) -> bytes:
    """A fixed-pitch text rendering of the table, paginated at 45 lines per page."""
    lines = [title, "", " | ".join(headers), "-" * 100]
    lines.extend(" | ".join(row) for row in rows)

    pages = [
        lines[index : index + _PDF_LINES_PER_PAGE]
        for index in range(0, max(len(lines), 1), _PDF_LINES_PER_PAGE)
    ] or [[title]]

    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # 1-based object number

    # Object numbering is fixed up front: 1 = catalog, 2 = pages, 3 = font, then a
    # (page, content) pair per page.
    page_object_numbers = [4 + 2 * index for index in range(len(pages))]
    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)

    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("latin-1"))
    add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, page_lines in enumerate(pages):
        content_number = page_object_numbers[index] + 1
        stream_lines = ["BT", "/F1 9 Tf", "11 TL", "36 756 Td"]
        for line in page_lines:
            stream_lines.append(f"({_pdf_escape(line)}) Tj T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1")
        add(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << "
            f"/F1 3 0 R >> >> /Contents {content_number} 0 R >>".encode("latin-1")
        )
        add(b"<< /Length " + str(len(stream)).encode("latin-1") + b" >>\nstream\n" + stream + b"\nendstream")

    out = BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode("latin-1"))
        out.write(body)
        out.write(b"\nendobj\n")

    xref_offset = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    return out.getvalue()


def build_file(export_format: str, title: str, headers: list[str], rows: list[list[str]]) -> bytes:
    if export_format == "Excel":
        return build_xlsx(title, headers, rows)
    return build_pdf(title, headers, rows)
