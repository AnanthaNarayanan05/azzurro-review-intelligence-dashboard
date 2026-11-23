"""Write SYNTHETIC sample files to data/sample/ for trying the import wizard.

Usage (from the repository root):
    backend/.venv/Scripts/python.exe -m scripts.generate_sample_files   (run inside backend/)

The files are invented demo data. Every row says SYNTHETIC in the "Data origin" column.
The anchor date is fixed so the committed files are reproducible.
"""

from datetime import date

from openpyxl import Workbook

from app.core.config import REPO_ROOT
from app.services.demo_data import CSV_COLUMNS, generate_rows, load_demo_properties, rows_to_csv

ANCHOR = date(2026, 11, 23)
OUT = REPO_ROOT / "data" / "sample"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = generate_rows(load_demo_properties(), ANCHOR)
    (OUT / "synthetic_reviews_sample.csv").write_bytes(rows_to_csv(rows))

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reviews"
    sheet.append(CSV_COLUMNS)
    for row in rows:
        sheet.append([row.get(column, "") for column in CSV_COLUMNS])
    workbook.save(OUT / "synthetic_reviews_sample.xlsx")
    print(f"Wrote {len(rows)} SYNTHETIC reviews to {OUT}")


if __name__ == "__main__":
    main()
