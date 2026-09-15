"""Generate a bundle of leaked .docx press releases.

Every document is publicly signed "Cellule Comms CERT.tg", but the OOXML core
metadata (docProps/core.xml) tells a different story. The documents actually
touched by one insider (`cp:lastModifiedBy`) each carry a flag fragment in their
`cp:keywords` field. Ordered by `dcterms:created`, those fragments spell the
flag. Documents edited by other people carry decoy keywords.

Run:  python3 gen.py   (writes *.docx to the challenge root)
"""

import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

INSIDER = "afanou.k"
FLAG = "NCTF{ooxml_core_xml_lastmodifiedby_leak}"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
<Application>Microsoft Office Word</Application><Company>CERT.tg</Company>
</Properties>"""


def document_xml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{body}</w:t></w:r></w:p></w:body></w:document>"
    )


def core_xml(created: str, modified_by: str, keywords: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        "<cp:coreProperties "
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:creator>Cellule Comms CERT.tg</dc:creator>"
        f"<cp:lastModifiedBy>{modified_by}</cp:lastModifiedBy>"
        f"<cp:keywords>{keywords}</cp:keywords>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>'
        "</cp:coreProperties>"
    )


# Split the flag into fragments for the insider's documents (in created order).
FRAGMENTS = ["NCTF{ooxml_", "core_xml_", "lastmodifiedby", "_leak}"]
assert "".join(FRAGMENTS) == FLAG

# (filename, created, lastModifiedBy, keywords, visible-body)
DOCS = [
    (
        "communique_03_hausse_tarifs.docx",
        "2025-03-02T09:00:00Z",
        "stagiaire.doc",
        "tarifs;energie",
        "Communiqué officiel concernant les tarifs.",
    ),
    (
        "communique_01_alerte.docx",
        "2025-01-14T07:30:00Z",
        INSIDER,
        FRAGMENTS[0],
        "Alerte de sécurité nationale.",
    ),
    (
        "communique_04_dementi.docx",
        "2025-04-20T18:45:00Z",
        "presse.externe",
        "dementi;rumeur",
        "Démenti formel des rumeurs.",
    ),
    (
        "communique_02_maj.docx",
        "2025-02-01T11:15:00Z",
        INSIDER,
        FRAGMENTS[1],
        "Mise à jour de la situation.",
    ),
    (
        "communique_05_bilan.docx",
        "2025-05-10T14:00:00Z",
        INSIDER,
        FRAGMENTS[3],
        "Bilan trimestriel.",
    ),
    (
        "communique_06_annexe.docx",
        "2025-03-25T16:20:00Z",
        INSIDER,
        FRAGMENTS[2],
        "Annexe technique.",
    ),
]


def write_docx(
    path: str, created: str, modified_by: str, keywords: str, body: str
) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("word/document.xml", document_xml(body))
        z.writestr("docProps/app.xml", APP_XML)
        z.writestr("docProps/core.xml", core_xml(created, modified_by, keywords))


def main() -> None:
    for fname, created, mby, kw, body in DOCS:
        write_docx(os.path.join(ROOT, fname), created, mby, kw, body)
    print(f"wrote {len(DOCS)} .docx files")


if __name__ == "__main__":
    main()
