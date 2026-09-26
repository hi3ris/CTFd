#!/usr/bin/env python3
"""Read OOXML core metadata from every .docx, keep the documents touched by the
insider, order them by creation time and concatenate their keyword fragments."""

import glob
import os
import re
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INSIDER = "afanou.k"


def field(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml)
    return m.group(1) if m else ""


def main() -> None:
    rows = []
    for path in glob.glob(os.path.join(ROOT, "*.docx")):
        with zipfile.ZipFile(path) as z:
            core = z.read("docProps/core.xml").decode()
        rows.append(
            {
                "modified_by": field(core, "cp:lastModifiedBy"),
                "created": field(core, "dcterms:created"),
                "keywords": field(core, "cp:keywords"),
            }
        )

    insider = [r for r in rows if r["modified_by"] == INSIDER]
    insider.sort(key=lambda r: r["created"])
    flag = "".join(r["keywords"] for r in insider)
    print(flag)


if __name__ == "__main__":
    main()
