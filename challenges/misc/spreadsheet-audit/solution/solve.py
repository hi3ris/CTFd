#!/usr/bin/env python3
"""Read the hidden 'chk' column from ledger.xlsx and rebuild the flag."""

import os

from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "..", "ledger.xlsx")


def main() -> None:
    wb = load_workbook(XLSX, data_only=True)
    ws = wb["Ledger"]

    # Locate the hidden column and its header.
    hidden_cols = [letter for letter, dim in ws.column_dimensions.items() if dim.hidden]
    col = hidden_cols[0]

    chars = []
    for row in range(2, ws.max_row + 1):
        value = ws[f"{col}{row}"].value
        if value is None:
            continue
        chars.append(chr(int(value)))
        if "".join(chars).endswith("}"):
            break
    print("".join(chars))


if __name__ == "__main__":
    main()
