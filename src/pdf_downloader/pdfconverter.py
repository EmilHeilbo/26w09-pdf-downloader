import sys
from os.path import isfile
from typing import final

from PyQt6.QtCore import QByteArray, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication


@final
class PDFConverter:
  def __init__(self):
    if sys.platform.startswith("linux") and isfile("/.dockerenv"):
      from pyvirtualdisplay.display import Display

      self.display = Display(visible=False, backend="xvfb")
    self.app = QApplication(sys.argv)
    self.view = QWebEngineView()
    self.pdf_data = b""
    self.finished = False
    self.bytes = QByteArray()

  def download_pdf(self, url: str):
    # Connect to load finished signal
    _ = self.view.loadFinished.connect(self._on_load_finished)
    # Load the URL
    self.view.load(QUrl(url))
    # Start event loop
    _ = self.app.exec()

  def _on_load_finished(self, success: bool):
    if success:
      # Generate PDF
      page = self.view.page()
      if page is None:
        print("QWebEnginePage is not available")
        self.finished = True
        return
      page.printToPdf(self._pdf_printed)
    else:
      print("Failed to load page")
      self.finished = True

  def _pdf_printed(self, pdf_data: QByteArray | bytes | bytearray | memoryview[int]):
    self.pdf_data = (
      bytes(pdf_data.data()) if isinstance(pdf_data, QByteArray) else bytes(pdf_data)
    )
    self.finished = True
    self.app.quit()  # Exit event loop

  def get_pdf(self, url: str) -> bytes:
    self.download_pdf(url)
    return self.pdf_data


# Usage
if __name__ == "__main__":
  downloader = PDFDownloader()
  pdf = downloader.get_pdf("https://example.com")
  if pdf:
    with open("output.pdf", "wb") as f:
      f.write(pdf)
