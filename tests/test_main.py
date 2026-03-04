import logging
from datetime import datetime, timezone
from hashlib import blake2b
from os import environ
from pathlib import Path
from random import random

import pytest
from diffpdf import diffpdf
from httpx import Client, ConnectError

import pdf_downloader as pdf

TEMP_PDF_PATH = (
  Path(environ["TEMP"].replace("\\", "/") or "/tmp")
  / f"pytest_{datetime.now(timezone.utc).date()}_{str(random())[2:10]}.pdf"
)


def test_download_pdf():
  Path("./reports.db").unlink(True)
  with Client(follow_redirects=False) as client:
    APP = pdf.Application(Path.cwd(), client)
    PDFS = {
      "https://pdfobject.com/pdf/sample.pdf": "d68d3c8ca80f17920649763a7c4cc597a7b4f1b9464674e8",
      "https://theanarchistlibrary.org/library/the-solarpunk-community-a-solarpunk-manifesto.pdf": "ce83e394beb7abd51751a8d5a4484b3ce30184809b6ff41d",
    }
    for url, hash in PDFS.items():
      success, test = APP.test_url(url)
      assert success
      assert test.headers["Content-Type"] == "application/pdf"
      _, response = APP.download_pdf(test)
      assert response.content.startswith("%PDF".encode("ascii"))
      assert (blake2b(response.content, digest_size=24).hexdigest()) == hash
      _, _ = APP.export_pdf(response, TEMP_PDF_PATH)


def test_html_to_pdf():
  with Client(follow_redirects=False) as client:
    APP = pdf.Application(Path.cwd(), client)
    URL = "https://example.com"
    success, test = APP.test_url(URL)
    assert success
    assert test.headers["Content-Type"].startswith("text/html")
    _, response = APP.download_pdf(test)
    logging.debug("Start of content: %s" % response.text[:15])
    assert "<!doctype html>" == response.text[:15].lower()
    logging.debug("PDF Path: %s" % TEMP_PDF_PATH)
    _, bytes = APP.export_pdf(response, TEMP_PDF_PATH)
    logging.debug(f"File written: {TEMP_PDF_PATH.exists()}")
    assert bytes.startswith("%PDF".encode("ascii"))
    assert diffpdf(Path.cwd() / Path("tests/docs/example.pdf"), TEMP_PDF_PATH)


def test_is_file_newer():
  TEST_TIME = datetime.strftime(
    datetime(1970, 1, 1, tzinfo=timezone.utc), "%a, %d %b %Y %H:%M:%S %Z"
  )
  TEST_FILE = Path.cwd() / "LICENSE"
  assert pdf.local_file_exists_and_is_newer(TEST_FILE, TEST_TIME)


def test_bad_responses():
  URL = "https://free.mockerapi.com/"
  with Client() as client:
    APP = pdf.Application(Path.cwd(), client)
    _, test_301 = APP.test_url(URL + "301")
    assert test_301.status_code == 301
    (_, test) = APP.test_url(URL + "200")
    assert test.is_success
    status, json_response = APP.download_pdf(test)
    assert not status
    assert json_response.headers["Content-Type"] == "application/json"


def test_expired_cert():
  URL = "https://expired.badssl.com"
  with Client() as client:
    with pytest.raises(ConnectError) as e:
      APP = pdf.Application(Path.cwd(), client)
      _ = APP.test_url(URL)
    assert "validity" in str(e.value)


# TODO: test download_pdf against empty body
# TODO: ensure URL protocol is r"https?:"
