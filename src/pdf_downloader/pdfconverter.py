import logging
import sys
from pathlib import Path
from typing import final

from PyQt6.QtCore import QByteArray, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication


@final
class PDFConverter:
  def __init__(self):
    if (
      sys.platform.startswith("linux") and Path("/.dockerenv").exists()
    ):  # pragma: no cover
      from pyvirtualdisplay.display import Display

      self.display = Display(visible=False, backend="xvfb").start()
    self.logger = logging.getLogger(__name__)
    self.app = QApplication(sys.argv)
    self.view = QWebEngineView()
    self.pdf_data = b""
    self.finished = False
    self.bytes = QByteArray()

  def download_pdf(self, url: str):
    # Connect to load finished signal
    self.logger.debug("Connecting to `loadFinished` signal")
    _ = self.view.loadFinished.connect(self._on_load_finished)
    # Load the URL
    self.logger.debug(f"Loading URL: {url}")
    self.view.load(QUrl(url))
    # FIXME: converter dies silently here when run in a Docker container, but works fine when run locally on Windows
    # Start event loop
    self.logger.debug("Starting event loop")
    _ = self.app.exec()

  def _on_load_finished(self, success: bool):
    if success:
      # Generate PDF
      page = self.view.page()
      if page is None:  # pragma: no cover
        self.logger.error("QWebEnginePage is not available")
        self.finished = True
        return
      self.logger.debug("Page loaded successfully, generating PDF")
      page.printToPdf(self._pdf_printed)
    else:  # pragma: no cover
      self.logger.error("Failed to load page")
      self.finished = True

  def _pdf_printed(self, pdf_data: QByteArray | bytes | bytearray | memoryview[int]):
    self.logger.debug("PDF generated, processing data")
    self.pdf_data = (
      bytes(pdf_data.data()) if isinstance(pdf_data, QByteArray) else bytes(pdf_data)
    )
    self.logger.debug(f"PDF data length: {len(self.pdf_data)} bytes")
    self.finished = True
    self.app.quit()  # Exit event loop

  def get_pdf(self, url: str) -> bytes:
    self.logger.debug(f"Getting PDF for URL: {url}")
    self.download_pdf(url)
    self.logger.debug("PDF download complete, returning data")
    return self.pdf_data
