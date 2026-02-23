import logging
from sys import argv


def main(args: list[str]) -> None:
  logging.basicConfig(level=logging.INFO)
  logging.info("Starting PDF Downloader")
  logging.debug(f"args: {', '.join(args)}")


if __name__ == "__main__":
  main(argv[1:])
