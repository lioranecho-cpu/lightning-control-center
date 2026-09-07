# Stage 1: download lncli for the target arch
FROM debian:bookworm-slim AS lncli-fetcher

ARG TARGETARCH
ARG LND_VERSION=0.18.3-beta

RUN apt-get update && apt-get install -y --no-install-recommends curl tar ca-certificates && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) GOARCH=amd64 ;; \
      arm64) GOARCH=arm64 ;; \
      *) echo "Unsupported arch: $TARGETARCH" && exit 1 ;; \
    esac; \
    curl -fsSL \
      "https://github.com/lightningnetwork/lnd/releases/download/v${LND_VERSION}/lnd-linux-${GOARCH}-v${LND_VERSION}.tar.gz" \
      -o /tmp/lnd.tar.gz; \
    tar -xzf /tmp/lnd.tar.gz -C /tmp; \
    cp "/tmp/lnd-linux-${GOARCH}-v${LND_VERSION}/lncli" /usr/local/bin/lncli; \
    chmod +x /usr/local/bin/lncli

# Stage 2: runtime image
FROM python:3.11-slim

WORKDIR /app

COPY --from=lncli-fetcher /usr/local/bin/lncli /usr/local/bin/lncli

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lcc_api.py .

# Frontend assets — copied into startos-pkg/ by `make frontend` before build
COPY *.html ./
COPY lcc-theme.js ./
COPY icons/ ./icons/

EXPOSE 8765

CMD ["uvicorn", "lcc_api:app", "--host", "0.0.0.0", "--port", "8765"]
