FROM ghcr.io/astral-sh/uv:python3.14-trixie

WORKDIR /app
# Install dependencies, copy minimum required files for `uv sync` to work
# RUN apk add gcc musl-dev qt6-qtwebengine-dev qt6-qtbase-dev
RUN uv venv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --no-install-project

# Copy the rest over and build
COPY . .
RUN uv build

# EXPOSE 8000
ENTRYPOINT [ "uv", "run", "-m", "pdf_downloader" ]
