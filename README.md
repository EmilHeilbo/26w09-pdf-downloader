# PDF Downloader

## Build / Run
To run the program it is recommended to have either `uv` or `docker` installed.

Create a folder named "out" in the project and copy the Excel file there as `base.xlsx`

### uv:
If you want to download all reports, append `--all` to `uv run -m pdf_downloader`

```sh
uv venv
uv sync
uv run -m pdf_downloader
```

### Docker:

```sh
docker build -t pdf_downloader .
docker run pdf_downloader
```

## Tests

To run tests, assuming you've set up a .venv with `uv`:
```sh
uv sync --all-extras
uv run -m coverage run -m pytest
uv run -m coverage report -m
```

## Requirements
Language: Python 3.14 (`uv`, `Docker` + `systemd`)
Libraries: httpx, pandas & pandera

### Software Requirements
- [x] Ingest Excel file -> find columns by 1st row value -> add to SQLite .db file
- [-] API-endpoint to add reports (both PDF-link and HTML-link) and download report PDFs
- [x] Download PDF-files
	- [x] Check if the file exists (and checksum matches)
	- [x] Compare `Last-Modified`-header with download time
	- [?] Validate downloaded PDF-files
	- [x] Save webpage as PDF if link doesn't point to a PDF
		- [x] Check if link redirects to eg. base URL with an empty path, a 404 page or similar
- [ ] Log errors to file

#### Optional
- Parallel downloads (async) with rate-limiting
- Authentication for API endpoints returning 401

### Documentation requirements
- UML diagrams
- Flow diagrams

### Questions:
- Does the Excel file change over time?
- Do files need to be downloaded once, or periodically?
- Should it be run manually or automatically (eg. cronjob)?
