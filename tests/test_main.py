from hashlib import blake2b
from pathlib import Path

from httpx import Client

from pdf_downloader.__main__ import Application


def test_download_pdf():
  with Client(follow_redirects=False) as client:
    APP = Application(Path.cwd(), client)
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


def test_html_to_pdf():
  with Client(follow_redirects=False) as client:
    APP = Application(Path.cwd(), client)
    URL = "https://docs.astral.sh/uv"
    success, test = APP.test_url(URL)
    assert success
    assert test.headers["Content-Type"].startswith("text/html")
    _, response = APP.download_pdf(test)
    assert response.text.startswith("<!DOCTYPE html>")
    _, bytes = APP.export_pdf(response, Path.cwd() / "temp.pdf")
    assert bytes.startswith("%PDF".encode("ascii"))
    # TODO: test contents of PDF
    # can't just do a simple hash compare
    # the converter adds some metadata to the PDF itself


# TODO: test with https://free.mockerapi.com/<status_code>
# TODO: test against eg. application/json
# TODO: test download_pdf against empty body
# TODO: test with https://badssl.com
# TODO: ensure URL protocol is r"https?:"
