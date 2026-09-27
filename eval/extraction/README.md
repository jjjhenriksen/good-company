# Fictional extraction benchmark

Run `python eval/extraction/run.py` with reportlab, Poppler (`pdftoppm`,
`pdftotext`) and Tesseract installed. The script deterministically generates three
pages spanning a food bank, arts program and nonprofit board, plus an image-only
scan PDF. Original row/date/role/condition pairs and exceptions are in fixtures.json.
Source locations are page/fixture IDs; the privacy audience comes from the trusted
manifest, never a document instruction.

Observed with Poppler 26.04.0 and Tesseract 5.5.2 on 2026-09-26:

| Method | Correct row associations | Exceptions | Privacy labels | Page locations |
| --- | --- | --- | --- | --- |
| Digital PDF, layout extraction | 6/6 | 3/3 | 3/3 | 3/3 |
| Image-only PDF, no OCR | 0/6 | 0/3 | 0/3 | 0/3 |
| Clean 150-DPI scan, OCR | 6/6 | 3/3 | 3/3 | 3/3 |

Rendered originals were visually checked for readable columns and unclipped
conditions. This small clean-scan corpus is a baseline, not evidence for noisy,
rotated, handwritten or complex multi-column documents. Empty scan extraction is
an observed failure requiring OCR and human review before ingestion; retrieval
cannot recover text that extraction omitted. Do not auto-classify private content
from an extracted heading. Committed artifacts and machine-readable results make
this run reviewable without any actual pilot document.
