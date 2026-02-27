from __future__ import annotations

import logging
import sqlite3 as sql
from os.path import isfile
from pathlib import Path
from sys import argv

import httpx
import pandas as pd


def main(args: list[str]) -> None:
  # with open("/app/config.toml", "rb") as file:
  #   CONFIG = tomllib.load(file)
  logging.basicConfig(level=logging.DEBUG)
  logging.info("Starting PDF Downloader")
  logging.debug(f"args: {', '.join(args)}")

  # Check if sqlite database exists, and if not, import base.xlsx into database using pandas
  try:
    IN_DOCKER = isfile("/.dockerenv")
    db_path = Path("/app/reports.db") if IN_DOCKER else Path.home() / "reports.db"
    excel_path = Path("/app/base.xlsx") if IN_DOCKER else Path.home() / "base.xlsx"
    _df = load_excel(db_path, excel_path)

  except Exception as e:
    logging.error(f"Error creating reports table from Excel sheet: {e}")


def load_excel(db_path: str | Path, excel_path: str | Path) -> pd.DataFrame:
  logging.debug(f"excel_path: {excel_path}, exists: {isfile(excel_path)}")
  logging.debug(f"db_path: {db_path}, exists: {isfile(db_path)}")
  with sql.connect(db_path) as conn:
    cursor = conn.cursor().execute(
      'SELECT name FROM sqlite_schema WHERE type="table" AND name="reports"'
    )
    if not cursor.fetchone():
      with open(excel_path, "rb") as f:
        df = pd.read_excel(f).rename(  # type: ignore[no-untyped-call]
          columns={
            "BRnum": "id",
            "Pdf_URL": "main_url",
            "Report Html Address": "fallback_url",
          }
        )
      _ = df.to_sql("reports", conn, index=False)  # type: ignore[no-untyped-call]
      logging.info("Created reports table from base.xlsx")
      return df
    return pd.read_sql("SELECT * FROM reports", conn)  # type: ignore[no-untyped-call]


def download_pdf(url: str, path: Path) -> None:
  with httpx.Client() as client:
    client.follow_redirects = False
    # Test if url is valid and returns a 2XX status code
    _ = client.get(url).raise_for_status()
    response = client.get(url)
    # TODO: Handle non-PDF URLs
    with open(path, "+wb") as file:
      _ = file.write(response.content)


if __name__ == "__main__":
  main(argv[1:])
