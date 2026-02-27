import logging
from hashlib import blake2s

import pdf_downloader.__main__ as pdf


def test_download_pdf():
  SAMPLE_PDF_URL = "https://pdfobject.com/pdf/sample.pdf"
  _, response = pdf.download_pdf(SAMPLE_PDF_URL)
  assert response.status_code == 200
  assert response.headers.get("Content-Type") == "application/pdf"
  assert (
    blake2s(response.content).hexdigest()
  ) == "69217a3079908094e11121d042354a7c1f55b6482ca1a51e1b250dfd1ed0eef9"
