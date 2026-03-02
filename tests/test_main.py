import logging
from hashlib import blake2s
from pathlib import Path

import httpx

import pdf_downloader.__main__ as pdf


def test_download_pdf():
  app = pdf.Application(Path.cwd(), httpx.Client(follow_redirects=False))
  SAMPLE_PDF_URL = "https://pdfobject.com/pdf/sample.pdf"
  _, test = app.test_url(SAMPLE_PDF_URL)
  assert test.status_code == 200
  assert test.headers.get("Content-Type") == "application/pdf"
  _, response = app.download_pdf(test)
  assert response.content.startswith("%PDF".encode("ascii"))
  assert (
    blake2s(response.content).hexdigest()
  ) == "69217a3079908094e11121d042354a7c1f55b6482ca1a51e1b250dfd1ed0eef9"
