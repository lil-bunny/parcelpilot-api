"""Generate scripts/_seed.sql from Excel (for manual or MCP apply)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook

from scripts.seed_postgres import TABLES, WORKBOOK, _sheet_rows


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main() -> None:
    wb = load_workbook(WORKBOOK, read_only=True, data_only=True)
    statements: list[str] = []
    for table in TABLES:
        for row in _sheet_rows(wb, table):
            cols = list(row.keys())
            colstr = ", ".join(cols)
            vals = ", ".join(sql_val(row[c]) for c in cols)
            statements.append(
                f"INSERT INTO {table} ({colstr}) VALUES ({vals}) ON CONFLICT DO NOTHING;"
            )
    wb.close()
    out = Path(__file__).resolve().parent / "_seed.sql"
    out.write_text("\n".join(statements), encoding="utf-8")
    print(f"Wrote {len(statements)} statements to {out}")


if __name__ == "__main__":
    main()
