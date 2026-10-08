# WILO connector server: wilo.mcp_server behind OAuth sign-in, for Cloud Run (#43, #31).
# Build:  docker build -t wilo-connector .
# Run:    PUBLIC_URL must be the service's public https:// address (it becomes the OAuth issuer).
#         Cloud Run sets $PORT. Credentials come from the runtime's service account (no key file in the image).
FROM python:3.14-slim

WORKDIR /app
COPY pyproject.toml ./
COPY wilo ./wilo
COPY config ./config
COPY schema ./schema
# Editable install: wilo/data.py reads config/ and schema/ relative to the repo root (/app).
RUN pip install --no-cache-dir -e . && useradd --create-home app && chown -R app /app
USER app

ENV PYTHONUNBUFFERED=1
# Fails fast if PUBLIC_URL is missing or not https:// (the server refuses to expose itself otherwise).
CMD ["sh", "-c", "exec python -m wilo.mcp_server --http --auth --public-url \"$PUBLIC_URL\""]
