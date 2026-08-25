"""Assert Excel sheet headers match Postgres migration columns."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook

from scripts.seed_postgres import TABLES, WORKBOOK, _norm_header, _sheet_rows

EXPECTED = {
    "accounts": {
        "account_id",
        "account_name",
        "plan",
        "status",
        "csm",
        "contract_file",
        "premium_support",
        "notes",
    },
    "orders": {
        "order_id",
        "account_id",
        "carrier",
        "status",
        "booked_at",
        "pickup_window_start",
        "pickup_window_end",
        "pickup_actual_at",
        "shipment_fee_inr",
        "carrier_fault",
        "customer_fault",
        "cancellation_requested_at",
        "notes",
    },
    "tickets": {
        "ticket_id",
        "account_id",
        "created_at",
        "status",
        "subject",
        "description",
        "channel",
        "assigned_to",
        "last_customer_message_at",
        "historical_resolution",
    },
}


def main() -> None:
    if not WORKBOOK.exists():
        print(f"Workbook not found: {WORKBOOK}")
        sys.exit(1)
    wb = load_workbook(WORKBOOK, read_only=True, data_only=True)
    ok = True
    for table in TABLES:
        rows = _sheet_rows(wb, table)
        if not rows:
            print(f"FAIL {table}: no data")
            ok = False
            continue
        headers = set(rows[0].keys())
        missing = EXPECTED[table] - headers
        extra = headers - EXPECTED[table]
        if missing:
            print(f"FAIL {table}: missing columns {sorted(missing)}")
            ok = False
        elif extra:
            print(f"WARN {table}: extra columns {sorted(extra)}")
        else:
            print(f"OK {table}: {len(rows)} rows, columns match")
    wb.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
