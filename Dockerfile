# Self-hosted trial image: the CRIS-SME local API runner + a live-mode build
# of the Assurance Console, served together behind nginx on one port. Intended
# for a client or evaluator to run against their own Azure/AWS credentials
# without needing separate frontend/backend hosting.
#
# Build:  docker build -t cris-sme .
# Run:    docker run -p 127.0.0.1:8080:8080 -v cris-sme-data:/data cris-sme
# Then:   open http://localhost:8080

FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS frontend-build
WORKDIR /app/frontend
COPY frontend/console/package.json frontend/console/package-lock.json ./
RUN npm ci
COPY frontend/console/ ./
RUN npm run build:selfhost

FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements/build.txt requirements/cloud.txt /app/requirements/
RUN pip install --no-cache-dir --require-hashes -r requirements/build.txt \
    && pip install --no-cache-dir --require-hashes -r requirements/cloud.txt
COPY pyproject.toml setup.py MANIFEST.in README.md LICENSE ./
COPY src/ ./src/
COPY data/ ./data/
RUN pip install --no-cache-dir --no-deps --no-build-isolation . \
    && pip check

COPY --from=frontend-build /app/frontend/dist/selfhost /app/console
COPY docker/nginx.conf /etc/nginx/sites-enabled/default
COPY docker/nginx-main.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && groupadd --gid 10001 cris \
    && useradd --uid 10001 --gid cris --create-home cris \
    && mkdir -p /data/outputs/reports /data/outputs/figures \
    && chown -R cris:cris /data

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
WORKDIR /data
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).close()"
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
