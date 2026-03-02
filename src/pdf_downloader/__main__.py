from __future__ import annotations

import logging
import re
import sqlite3 as sql
from datetime import date, datetime
from os.path import isfile
from pathlib import Path
from sys import argv

import httpx
import pandas as pd
from PyQt6.QtCore import QEventLoop
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication


def main(args: list[str]) -> None:
  logging.basicConfig(level=logging.DEBUG)
  logging.info("Starting PDF Downloader")
  logging.debug(f"Running in: {Path.cwd()}")
  logging.debug(f"args: {', '.join(args)}")
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

  # Check if sqlite database exists, and if not, import base.xlsx into database using pandas
  try:
    # Check if we're in a Docker container
    DOCKER = isfile("/.dockerenv")
    db_path = Path("/app/reports.db") if DOCKER else Path.cwd() / "reports.db"
    excel_path = Path("/app/base.xlsx") if DOCKER else Path.cwd() / "base.xlsx"
    _df = load_main_table(db_path, excel_path)

  except Exception as e:
    logging.error(f"Error creating reports table from Excel sheet: {e}")


def load_main_table(db_path: Path, excel_path: Path) -> pd.DataFrame:
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


def download_pdf(
  url: str, cutoff_date: date | None = None
) -> tuple[bool, httpx.Response]:
  """Download a PDF from a URL, returning a tuple of success status and response"""
  with httpx.Client() as client:
    client.follow_redirects = False
    test = client.head(url)
    if not test.is_success:
      logging.warning(
        f"HEAD request failed for {url} with status code {test.status_code}"
      )
      return (False, test)
    mod_date = datetime.strptime(
      test.headers["Last-Modified"] or "Thu, 01 Jan 1970 00:00:00 GMT",
      "%a, %d %b %Y %H:%M:%S %Z",
    ).date()
    if cutoff_date and cutoff_date >= mod_date:
      logging.info(f"Report at {url} is older than cutoff date, skipping download")
      return (False, test)
    _type: str = test.headers["Content-Type"] or "none"
    logging.debug(f"HEAD request for {url} returned Content-Type: {_type}")
    if re.match(r"((text/html)|(application/pdf))(; charset=utf-8)?", _type):
      return (test.is_success, test)
    return (lambda response: (response.is_success, response))(client.get(url))


def save_pdf(input: httpx.Response, destination: Path) -> bool:
  """Save a PDF from a response to a file, returning True if successful"""
  if input.headers.get("Content-Type") == "application/pdf":
    with open(destination, "+wb") as file:
      _ = file.write(input.content)
      return True
  return convert_to_pdf(input, destination)


def convert_to_pdf(input: httpx.Response, output_path: Path) -> bool:
  """Attempt to convert a HTML response to PDF, returning the success status"""
  if "text/html" in input.headers.get("Content-Type"):
    # Convert HTML to PDF using PyQt6, returning the PDF as bytes
    _app = QApplication.instance() or QApplication(argv)

    view = QWebEngineView()
    page = view.page()
    if page is None:
      raise RuntimeError("QWebEnginePage is not available")

    # Wait for page to load
    load_loop = QEventLoop()
    _ = page.loadFinished.connect(load_loop.quit)
    view.setHtml(input.text)
    _ = load_loop.exec()

    # Prepare for PDF generation
    print_loop = QEventLoop()

    # Save directly to file
    page.printToPdf(output_path.as_posix())
    _ = print_loop.exec()
  # Check if PDF file was created
  if isfile(output_path):
    with open(output_path, "rb", 4) as f:
      return f.read().startswith("%PDF".encode("ascii"))
  return False


if __name__ == "__main__":
  main(argv[1:])
