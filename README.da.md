# PDF Downloader

## Krav
Kodesprog: Python 3.14 (`uv`, `Docker` + `systemd`)
Biblioteker: pandas, prisma, httpx, toml-rs, fastapi

### Softwarekrav
- Læs Excel-fil, find kolonner efter værdi i 1. række, tilføj til SQLite .db-fil
- API-endpoint til at tilføje rapporter (begge PDF-link og HTML-link) og download rapport PDFs
- Download PDF-filer
	- Kontroller om filen findes (og checksum matcher)
	- Sammenlign `Last-Modified`-header med downloadtidspunkt
	- Valider downloadede PDF-filer
	- Gem webside som PDF hvis link ikke peger på en PDF
		- Kontroller om link omdirigerer til f.eks. basis-URL med tom sti, en 404-side eller lignende

#### Valgfri
- Parallelliserede downloads (async) med rate-limiting
- Authn for API-endpoints, der returnerer 401

### Dokumentationskrav
- UML-diagrammer
- Flowdiagrammer

### Spørgsmål:
- Ændres Excel-filen over tid?
- Skal filer downloades én gang eller periodisk?
- Skal det være manuelt eller automatisk (f.eks. cronjob)?
