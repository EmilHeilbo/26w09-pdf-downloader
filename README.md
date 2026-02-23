# PDF Downloader

## Requirements
Language: Python 3.14 (`uv`, `Docker` + `systemd`)
Libraries: pandas, prisma, httpx, toml-rs, fastapi

### Software Requirements
- Ingest Excel file -> find columns by 1st row value -> add to SQLite .db file
- API-endpoint to add reports (both PDF-link and HTML-link) and download report PDFs
- Download PDF-files
	- Check if the file exists (and checksum matches)
	- Compare `Last-Modified`-header with download time
	- Validate downloaded PDF-files
	- Save webpage as PDF if link doesn't point to a PDF
		- Check if link redirects to eg. base URL with an empty path, a 404 page or similar

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
