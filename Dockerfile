FROM ghcr.io/astral-sh/uv:python3.14-trixie

# Install dependencies
RUN apt update
RUN /bin/bash -c "apt install -y libqt6{webenginecore,webview,gui}6 xvfb x11-utils gnumeric"
RUN useradd -b / -m -s /bin/bash app

# Copy minimum required files for `uv sync` to work
USER app
WORKDIR /app
RUN ls -la .
RUN uv venv
COPY --chown=app: pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --no-install-project

# Copy the rest over and build
COPY --chown=app: . .
RUN uv build

# EXPOSE 8000
ENTRYPOINT [ "uv", "run", "-m", "src.pdf_downloader" ]
