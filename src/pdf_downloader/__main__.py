from __future__ import annotations

import logging
import sqlite3 as sql
from datetime import datetime
from os.path import isfile
from pathlib import Path
from sys import argv
from typing import final

import pandera.pandas as pa
from httpx import Client, Response
from pandas import (
  DataFrame,
  read_sql,  # type: ignore[no-untyped-call]
)

from .pdfconverter import PDFConverter


def local_file_exists_and_is_newer(local_file: Path, date_header: str | None) -> bool:
  if not date_header:
    return True
  if not local_file.exists():
    return False
  local_date = datetime.fromtimestamp(local_file.stat().st_mtime).date()
  online_date = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z").date()
  return local_date >= online_date


@final
class Application:
  """
  Main application class for PDF Downloader

  Regular download flow: `test_url(url)` |> `True, download_pdf()` |> `True, export_pdf()`
  """

  SCHEMA = pa.DataFrameSchema(
    {
      "report_id": pa.Column(str, nullable=False),
      "main_url": pa.Column(str, nullable=False),
      "fallback_url": pa.Column(str, nullable=False),
    },
    strict=True,
    coerce=True,
  )

  def load_main_table(self, excel_path: Path) -> DataFrame:
    """Load the reports table from the database, or create it from the Excel file if it doesn't exist"""
    self.LOGGER.debug(f"excel_path: {excel_path}, exists: {isfile(excel_path)}")
    self.LOGGER.debug(f"db_path: {self.DATABASE}, exists: {isfile(self.DATABASE)}")
    with sql.connect(self.DATABASE) as conn:
      cursor = conn.cursor().execute(
        'SELECT name FROM sqlite_schema WHERE type="table" AND name="reports"'
      )
      if not cursor.fetchone():
        with open(excel_path, "rb") as f:
          from pandas import read_excel  # type: ignore[no-untyped-call]

          columns = ["BRnum", "Pdf_URL", "Report Html Address"]
          new_columns = ["report_id", "main_url", "fallback_url"]
          df = (
            read_excel(f, dtype=str)[columns]
            .rename(columns=dict(zip(columns, new_columns)))
            .fillna("")
          )
          # Strip leading/trailing whitespace from URLs
          for col in df.columns:
            df[col] = df[col].str.strip()
        _ = df.to_sql("reports", conn, index_label="id", index=False)  # type: ignore[no-untyped-call]
        self.LOGGER.info("Created reports table from base.xlsx")
        return self.SCHEMA.validate(df)
      return self.SCHEMA.validate(read_sql('SELECT * from "reports"', conn))

  def __init__(self, base_dir: Path, client: Client):
    self.CLIENT = client
    self.CONVERTER = PDFConverter()
    self.DATABASE: Path = base_dir / "reports.db"
    self.LOGGER = logging.getLogger(__name__)
    self.REPORTS_DIR: Path = base_dir / "reports" / f"{datetime.today().date()}"
    self.REPORTS_TABLE = self.load_main_table(base_dir / "base.xlsx")

  def test_url(self, url: str) -> tuple[bool, Response]:
    response = self.CLIENT.head(url)
    if not response.is_success:
      self.LOGGER.warning(f"HEAD request failed for {url}")
      self.LOGGER.warning(f"{response.status_code}: {response.reason_phrase}")
      if response.is_redirect:
        self.LOGGER.warning(f"URL redirects to {response.headers['Location']}")

    return (lambda response: (response.is_success, response))(self.CLIENT.head(url))

  def download_pdf(self, input: Response) -> tuple[bool, Response]:
    """Download a PDF from a URL, returning a tuple of success status and response"""
    ACCEPTED_TYPES = ["text/html", "application/pdf"]
    # Check if the content type is HTML or PDF
    _type: str = input.headers["Content-Type"] or "none"
    self.LOGGER.debug(f"HEAD request for {input.url} returned Content-Type: {_type}")
    if any(_type.startswith(t) for t in ACCEPTED_TYPES):
      return (lambda response: (response.is_success, response))(
        self.CLIENT.get(input.url)
      )
    return (False, input)

  def export_pdf(self, input: Response, destination: Path) -> tuple[bool, bytes]:
    """
    Save a PDF from a response to a file, returning True if successful. Will also return the bytes of the PDF for testing purposes.

    If the response is HTML, convert to PDF using the PDFConverter class before saving.
    """
    if "application/pdf" in input.headers["Content-Type"]:
      if not len(input.content):
        input = self.CLIENT.get(input.url).raise_for_status()
      with open(destination, "wb") as file:
        _ = file.write(input.content)
        return True, input.content
    if "text/html" in input.headers["Content-Type"]:
      pdf_bytes = self.CONVERTER.get_pdf(str(input.url))
      if pdf_bytes.startswith("%PDF".encode("ascii")):
        with open(destination, "wb") as file:
          _ = file.write(pdf_bytes)
          return True, pdf_bytes
    return False, b""  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
  args = argv[1:]
  LOGGER = logging.getLogger(__name__)
  logging.basicConfig(
    level=logging.DEBUG,
    filename=Path.cwd() / "debug.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
  )
  LOGGER.info("Starting PDF Downloader")
  LOGGER.debug(f"Running in Docker: {isfile('/.dockerenv')}")
  LOGGER.debug(f"Running in: {Path.cwd()}")
  LOGGER.debug(f"args: {', '.join(args)}")

  # Use arguments to define app dir
  d_args: list[dict[str, str]] = []
  for arg in args:
    if arg.startswith("-"):
      if "=" in arg:
        args.remove(arg)
        args += arg.split("=", 1)
  for i in range(len(args)):
    if args[i].startswith("-"):
      d_args.append({args[i]: args[i + 1]})
    else:
      if len(args) > i + 1 and not args[i + 1].startswith("-"):
        raise RuntimeError("Launch arguments are invalid.")

  # Treat redirects as errors, to ignore landing pages for broken URLs
  with Client(follow_redirects=False) as client:
    found_reports: dict[str, Response] = {}
    cached_reports: dict[str, Response] = {}
    missing_reports: dict[str, str] = {}

    try:
      app = Application(Path.cwd(), client)
    except Exception as e:
      LOGGER.error(f"Error creating reports table from Excel sheet: {e}")
      exit(1)

    for _, row in app.REPORTS_TABLE.iterrows():
      file = app.REPORTS_DIR / f"{row['report_id']}.pdf"
      # catch SSL errors and other exceptions from httpx, and add to missing_reports with error message
      valid_responses: list[Response] = []
      for url in row["main_url", "fallback_url"]:  # type: ignore[index]
        if url and isinstance(url, str):
          try:
            _, response = app.test_url(url)
            valid_responses.append(response)
          except Exception as e:
            LOGGER.error(f"Error testing URL {url} for report {row['report_id']}: {e}")
            pass

      if any(r.is_success for r in valid_responses):
        response = valid_responses[0]
        LOGGER.info(f"{row['report_id']}: available at {valid_responses[0].url}")

        if local_file_exists_and_is_newer(file, response.headers["Last-Modified"]):
          LOGGER.info(f"{row['report_id']}: cached locally and up to date")
          cached_reports[row["report_id"]] = response
          continue

        found_reports[row["report_id"]] = response
        continue

      elif any(r.is_redirect for r in valid_responses):
        err = (
          f"URL redirected to: {[r for r in valid_responses if r.is_redirect][0]}"
          + ", please check the URL manually to find the new location of the report"
        )
        LOGGER.warning(f"{row['report_id']}: {err}")
        missing_reports[row["report_id"]] = err

      elif len(valid_responses) > 0:
        err = "Both URLs returned non-success status codes: " + ", ".join(
          f"{r.status_code} for {r.url}" for r in valid_responses
        )
        LOGGER.warning(f"{row['report_id']}: {err}")
        missing_reports[row["report_id"]] = err

      else:
        err = "URLs are invalid or unreachable"
        LOGGER.error(f"{row['report_id']}: {err}")
        missing_reports[row["report_id"]] = err

  # Download and save reports that are found and not cached
  for report_id, response in found_reports.items():
    if app.export_pdf(response, app.REPORTS_DIR / f"{report_id}.pdf"):
      LOGGER.info(f"Report {report_id} saved successfully")
    else:
      LOGGER.error(f"Failed to save report {report_id}")
