from __future__ import annotations

import logging
import re
import sqlite3 as sql
from datetime import date, datetime
from os.path import isfile
from pathlib import Path
from sys import argv
from typing import final

import httpx
from pandas import (
  DataFrame,
  read_sql,  # type: ignore[no-untyped-call]
)

from .pdfconverter import PDFConverter


def local_exists_and_is_newer(local_file: Path, date_header: str | None) -> bool:
  if not date_header:
    return True
  if not local_file.exists():
    return False
  local_date = datetime.fromtimestamp(local_file.stat().st_mtime).date()
  online_date = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z").date()
  return local_date >= online_date


def main(args: list[str]) -> None:
  logging.basicConfig(level=logging.DEBUG)
  logging.info("Starting PDF Downloader")
  logging.debug(f"Running in Docker: {isfile('/.dockerenv')}")
  logging.debug(f"Running in: {Path.cwd()}")
  logging.debug(f"args: {', '.join(args)}")

  # Use arguments to define app dir
  # d_args: list[dict[str, str]] = []
  # for arg in args:
  #   if arg.startswith("-"):
  #     if "=" in arg:
  #       args.remove(arg)
  #       args += arg.split("=", 1)
  # for i in range(len(args)):
  #   if args[i].startswith("-"):
  #     d_args.append({args[i]: args[i + 1]})
  #   else:
  #     if len(args) > i + 1 and not args[i + 1].startswith("-"):
  #       raise RuntimeError("Launch arguments are invalid.")

  try:
    _app = Application(Path.cwd())
    found_reports: list[dict[str, httpx.Response]] = []
    missing_reports: list[dict[str, str]] = []
    for _, row in _app.REPORTS.iterrows():
      file = _app.REPORTS_DIR / f"{row['report_id']}.pdf"
      # TODO: add good_url/bad_url handling, so one row can't be in both found and missing
      for url in row["main_url", "fallback_url"]:
        if not url:
          pass
        if isinstance(url, str):
          status, response = _app.test_url(url)
          if not status:
            missing_reports += {row["report_id"]: response}
            return
          if local_exists_and_is_newer(file, response.headers["Last-Modified"]):
            return
          found_reports += {row["report_id"]: response}

  except Exception as e:
    logging.error(f"Error creating reports table from Excel sheet: {e}")


@final
class Application:
  """Main application class for PDF Downloader"""

  def load_main_table(self, excel_path: Path) -> DataFrame:
    """Load the reports table from the database, or create it from the Excel file if it doesn't exist"""
    logging.debug(f"excel_path: {excel_path}, exists: {isfile(excel_path)}")
    logging.debug(f"db_path: {self.DATABASE}, exists: {isfile(self.DATABASE)}")
    with sql.connect(self.DATABASE) as conn:
      cursor = conn.cursor().execute(
        'SELECT name FROM sqlite_schema WHERE type="table" AND name="reports"'
      )
      if not cursor.fetchone():
        with open(excel_path, "rb") as f:
          from pandas import read_excel  # type: ignore[no-untyped-call]

          df = (
            read_excel(f)[["BRnum", "Pdf_URL", "Report Html Address"]]
            .fillna("")
            .rename(
              columns={
                "BRnum": "report_id",
                "Pdf_URL": "main_url",
                "Report Html Address": "fallback_url",
              }
            )
          )
          # Strip leading/trailing whitespace from URLs
          df["main_url"] = df["main_url"].str.strip()
          df["fallback_url"] = df["fallback_url"].str.strip()
        _ = df.to_sql("reports", conn, index_label="id", index=False)  # type: ignore[no-untyped-call]
        logging.info("Created reports table from base.xlsx")
        return df
      return read_sql('SELECT * from "reports"', conn)

  def __init__(self, base_dir: Path, client: httpx.Client):
    self.CLIENT = client
    self.CONVERTER = PDFConverter()
    self.DATABASE: Path = base_dir / "reports.db"
    self.REPORTS: DataFrame = self.load_main_table(base_dir / "base.xlsx")
    self.REPORTS_DIR: Path = base_dir / "reports" / f"{datetime.today().date()}"

  def test_url(self, url: str) -> tuple[bool, httpx.Response]:
    response = self.CLIENT.head(url)
    if not response.is_success:
      logging.warning(f"HEAD request failed for {url}")
      logging.warning(f"{response.status_code}: {response.reason_phrase}")
      if response.is_redirect:
        logging.warning(f"URL redirects to {response.headers['Location']}")

    return (lambda response: (response.is_success, response))(self.CLIENT.head(url))

  def download_pdf(self, input: httpx.Response) -> tuple[bool, httpx.Response]:
    """Download a PDF from a URL, returning a tuple of success status and response"""
    # Treat redirects as errors, to ignore landing pages on missing URL paths
    # Check if the content type is HTML or PDF
    _type: str = input.headers["Content-Type"] or "none"
    logging.debug(f"HEAD request for {input.url} returned Content-Type: {_type}")
    if any(_type.startswith(t) for t in ("text/html", "application/pdf")):
      return (lambda response: (response.is_success, response))(
        self.CLIENT.get(input.url)
      )
    return (False, input)

  def save_pdf(self, input: httpx.Response, destination: Path) -> bool:
    """Save a PDF from a response to a file, returning True if successful"""
    if input.headers["Content-Type"].startswith("application/pdf"):
      if not len(input.content):
        input = httpx.get(input.url).raise_for_status()
      with open(destination, "wb") as file:
        _ = file.write(input.content)
        return True
    if input.headers["Content-Type"].startswith("text/html"):
      pdf_bytes = self.CONVERTER.get_pdf(str(input.url))
      if pdf_bytes.startswith("%PDF".encode("ascii")):
        with open(destination, "wb") as file:
          _ = file.write(pdf_bytes)
          return True
    return False


if __name__ == "__main__":
  main(argv[1:])
