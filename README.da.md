# PDF Downloader

## Build / Run
For at køre programmet er det anbefalet at have enten `uv` eller `docker` installeret.

Opret en mappe ved navn "out" i projektet og kopier Excel-filen over som `base.xlsx`

### uv:
Hvis du vil downloade alle rapporter, afslut `uv run -m pdf_downloader` med `--all`

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

For at køre tests, hvis du har oprettet et .venv med `uv`:
```sh
uv sync --all-extras
uv run -m coverage run -m pytest
uv run -m coverage report -m
```

## Krav
Kodesprog: Python 3.14 (`uv`, `Docker` + `systemd`)
Biblioteker: httpx, pandas & pandera

### Softwarekrav
- [x] Læs Excel-fil, find kolonner efter værdi i 1. række, tilføj til SQLite .db-fil
- [ ] API-endpoint til at tilføje rapporter (begge PDF-link og HTML-link) og download rapport PDFs
- [x] Download PDF-filer
	- [x] Kontroller om filen findes (og checksum matcher)
	- [x] Sammenlign `Last-Modified`-header med downloadtidspunkt
	- [ ] Valider downloadede PDF-filer
	- [x] Gem webside som PDF hvis link ikke peger på en PDF
	- [x] Kontroller om link omdirigerer til f.eks. basis-URL med tom sti, en 404-side eller lignende

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
