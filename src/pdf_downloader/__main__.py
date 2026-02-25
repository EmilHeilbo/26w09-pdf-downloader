from __future__ import annotations

import logging
import sqlite3 as sql
import tomllib
from sys import argv

from pandas import read_excel  # type: ignore[reportUnknownVariableType]


def main(args: list[str]) -> None:
  with open("config.toml", "rb") as file:
    CONFIG = tomllib.load(file)
  logging.basicConfig(level=logging.INFO)
  logging.info("Starting PDF Downloader")
  logging.debug(f"args: {', '.join(args)}")

  # Check if sqlite database exists, and if not, import base.xlsx into database using pandas
  try:
    load_excel(
      CONFIG["settings"]["db_path"] or "reports.db",
      CONFIG["settings"]["excel_path"] or "base.xlsx",
    )
  except Exception as e:
    logging.error(f"Error creating reports table from Excel sheet: {e}")


def load_excel(db_path: str, excel_path: str) -> None:
  with sql.connect(db_path) as conn:
    table = conn.cursor().execute(
      'SELECT name FROM sqlite_schema WHERE type="table" AND name="reports"'
    )
    if not table.fetchone():
      with open(excel_path, "rb") as f:
        df = read_excel(f).rename(
          columns={
            "BRnum": "id",
            "Pdf_URL": "main_url",
            "Report Html Address": "fallback_url",
          }
        )
        _ = df.to_sql("reports", conn, index=False)  # type: ignore[reportUnknownVariableType]
        conn.commit()
        logging.info("Created reports table from base.xlsx")


if __name__ == "__main__":
  main(argv[1:])
