import logging
import sqlite3 as sql
from datetime import datetime
from pathlib import Path
from typing import final

import pandera.pandas as pa
from httpx import Client, Response
from pandas import (
  DataFrame,
  read_sql,  # type: ignore[no-untyped-call]
)

from .pdfconverter import PDFConverter


@final
class Application:
  """
  Main application class for PDF Downloader

  Regular download flow: `test_url(url)` -> `True, download_pdf()` -> `True, export_pdf()`
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
    self.LOGGER.debug(f"excel_path: {excel_path}, exists: {excel_path.exists()}")
    self.LOGGER.debug(f"db_path: {self.DATABASE}, exists: {self.DATABASE.exists()}")
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
        self.LOGGER.warning(
          f"URL redirects to {response.headers.get('Location', 'N/A')}"
        )

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
      if not len(input.content):  # pragma: no cover
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
