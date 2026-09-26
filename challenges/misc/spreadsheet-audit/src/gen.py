#!/usr/bin/env python3
"""Build ledger.xlsx for the spreadsheet-audit challenge.

The workbook looks like a mundane sales ledger. A hidden column holds one
Unicode code point per flag character (integers, not the literal text), so the
flag is never stored as plaintext. Un-hiding that column and mapping the code
points through ``chr`` reconstructs the flag.
"""

import os
import random

from openpyxl import Workbook

FLAG = "NCTF{hidden_columns_still_ship_data}"
REGIONS = ["Lomé", "Kara", "Sokodé", "Kpalimé", "Atakpamé"]


def main() -> None:
    rng = random.Random(4242)
    wb = Workbook()
    ws = wb.active
    ws.title = "Ledger"

    headers = ["Date", "Region", "Units", "UnitPrice", "Revenue", "chk"]
    ws.append(headers)

    codes = [ord(c) for c in FLAG]
    n_rows = max(len(codes), 40)
    for i in range(n_rows):
        day = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        region = rng.choice(REGIONS)
        units = rng.randint(1, 250)
        price = round(rng.uniform(2.0, 99.0), 2)
        revenue = round(units * price, 2)
        chk = codes[i] if i < len(codes) else rng.randint(32, 126)
        ws.append([day, region, units, price, revenue, chk])

    # Hide the "chk" column (F) and set it narrow so it reads as a scratch cell.
    ws.column_dimensions["F"].hidden = True
    ws.column_dimensions["F"].width = 3

    out = os.path.join(os.path.dirname(__file__), "..", "ledger.xlsx")
    wb.save(out)
    print("wrote", os.path.relpath(out), "rows:", n_rows)


if __name__ == "__main__":
    main()
