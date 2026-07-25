# Self-hosted trial image: the CRIS-SME local API runner + a live-mode build
# of the Assurance Console, served together behind nginx on one port. Intended
# for a client or evaluator to run against their own Azure/AWS credentials
# without needing separate frontend/backend hosting.
#
# Build:  docker build -t cris-sme .
# Run:    docker run -p 8080:8080 -v cris-sme-data:/data cris-sme
# Then:   open http://localhost:8080

FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/console/package.json frontend/console/package-lock.json ./
RUN npm ci
COPY frontend/console/ ./
RUN npm run build:selfhost

FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir '.[azure,aws]'

COPY --from=frontend-build /app/frontend/dist/selfhost /app/console
COPY docker/nginx.conf /etc/nginx/sites-enabled/default
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /data/outputs/reports /data/outputs/figures

VOLUME ["/data"]
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
