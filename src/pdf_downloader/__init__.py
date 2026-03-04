from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from sys import argv

from httpx import Client, Response

from .application import Application
from .pdfconverter import PDFConverter

# Export local functions and module classes
__all__ = ["local_file_exists_and_is_newer", "main", "Application", "PDFConverter"]


def local_file_exists_and_is_newer(local_file: Path, date_header: str | None) -> bool:
  tests: list[bool] = []
  tests.append(local_file.exists())
  if date_header and tests[0]:
    local_date = datetime.fromtimestamp(local_file.stat().st_mtime).date()
    online_date = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z").date()
    tests.append(local_date >= online_date)
  return all(x for x in tests)


def main(args: list[str] | None = None):  # pragma: no cover
  if args is None:
    args = []
  OUTPUT_DIR = Path.cwd() / "out"
  if not OUTPUT_DIR.exists():
    OUTPUT_DIR.mkdir()
  LOGGER = logging.getLogger(__name__)
  logging.basicConfig(
    level=logging.DEBUG,
    filename=OUTPUT_DIR / "debug.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
  )
  LOGGER.info("Starting PDF Downloader")
  LOGGER.debug(f"Running in Docker: {Path('/.dockerenv').exists()}")
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
  if not any(arg in args for arg in ["-A", "--all"]):
    logging.info("Launch arguments don't contain '-A' or '--all', exiting...")
  with Client(follow_redirects=False) as client:
    found_reports: dict[str, Response] = {}
    cached_reports: dict[str, Response] = {}
    missing_reports: dict[str, str] = {}

    try:
      app = Application(OUTPUT_DIR, client)
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


if __name__ == "__main__":  # pragma: no cover
  main(argv[1:])
