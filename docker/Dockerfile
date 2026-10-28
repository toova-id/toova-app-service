# syntax=docker/dockerfile:1.7
#
# Odoo 16 Engine - Optimized Dockerfile
#
# Optimizations:
# - Multi-stage build for smaller image
# - Layer caching for faster rebuilds
# - Remove unnecessary packages and files
# - Strip tests, docs, locales
# - Non-root user
# - Multi-arch support (amd64, arm64)
#
# Build:
#   docker buildx build --platform linux/amd64,linux/arm64 -f docker/Dockerfile -t odoo-16-engine .
#
ARG PYTHON_VERSION=3.12

# ============================================================
# Stage 1: Python wheels (build-time dependencies)
# ============================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS wheels
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc git \
        libffi-dev libjpeg62-turbo-dev libldap2-dev libpq-dev libsasl2-dev \
        libssl-dev libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/wheelhouse -r requirements.txt

# ============================================================
# Stage 2: Node.js and npm (for RTLCSS only)
# ============================================================
FROM node:22-slim AS node-builder
RUN npm install -g rtlcss@4

# ============================================================
# Stage 3: Managed React client
# ============================================================
FROM node:22-slim AS frontend-builder
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
COPY managed/ /src/managed/
RUN npm run build

# ============================================================
# Stage 4: Runtime (minimal)
# ============================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
ARG TARGETARCH
ARG ODOO_UID=101
ARG ODOO_GID=101
ARG ODOO_LOCALES=id,en_US
ARG ODOO_STRIP_TESTS=1
ARG WKHTMLTOPDF_VERSION=0.12.6.1-3
ARG WKHTMLTOPDF_AMD64_SHA256=98ba0d157b50d36f23bd0dedf4c0aa28c7b0c50fcdcdc54aa5b6bbba81a3941d
ARG WKHTMLTOPDF_ARM64_SHA256=b6606157b27c13e044d0abbe670301f88de4e1782afca4f9c06a5817f3e03a9c

# Environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MALLOC_ARENA_MAX=2

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fontconfig \
        fonts-dejavu-core \
        fonts-noto-core \
        libffi8 \
        libjpeg62-turbo \
        libldap-2.5-0 \
        libpq5 \
        libsasl2-2 \
        libssl3 \
        libxml2 \
        libxslt1.1 \
        libwebp7 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && groupadd --gid "${ODOO_GID}" odoo \
    && useradd --uid "${ODOO_UID}" --gid "${ODOO_GID}" --home-dir /var/lib/odoo --create-home odoo \
    && mkdir -p /etc/odoo /mnt/extra-addons /var/lib/odoo \
    && chown -R odoo:odoo /etc/odoo /mnt/extra-addons /var/lib/odoo

# Install Python wheels without copying wheelhouse into a persistent runtime layer.
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=bind,from=wheels,source=/wheelhouse,target=/wheelhouse \
    pip install --no-index --find-links=/wheelhouse -r /tmp/requirements.txt \
    && pip install --no-index --find-links=/wheelhouse setuptools \
    # Clean up Python cache
    && find /usr/lib/python3.12 -type f -name "*.pyc" -delete \
    && find /usr/lib/python3.12 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf /tmp/requirements.txt

# Install RTLCSS
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-builder /usr/local/bin/rtlcss /usr/local/bin/rtlcss

# Install pinned wkhtmltopdf patched-Qt package for target architecture.
RUN case "${TARGETARCH}" in \
        amd64) checksum="${WKHTMLTOPDF_AMD64_SHA256}" ;; \
        arm64) checksum="${WKHTMLTOPDF_ARM64_SHA256}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --location --retry 3 --output /tmp/wkhtmltox.deb \
        "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.bookworm_${TARGETARCH}.deb" \
    && echo "${checksum}  /tmp/wkhtmltox.deb" | sha256sum --check --strict - \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/wkhtmltox.deb

# Prune source before copying it into runtime, so removed files never remain in a lower layer.
FROM python:${PYTHON_VERSION}-slim-bookworm AS source-pruner
ARG ODOO_LOCALES=id,en_US
ARG ODOO_STRIP_TESTS=1
WORKDIR /src
COPY . /src
RUN python /src/scripts/prune_translations.py /src --locales "${ODOO_LOCALES}" --apply \
    && if [ "${ODOO_STRIP_TESTS}" = "1" ]; then \
        find /src/src/odoo/addons /src/src/addons /src/managed -type d -name tests -prune -exec rm -rf '{}' +; \
        find /src/src/odoo/addons /src/src/addons /src/managed -mindepth 1 -maxdepth 1 -type d -name 'test_*' -prune -exec rm -rf '{}' +; \
    fi \
    && rm -rf /src/.git /src/.github /src/.tx /src/doc /src/docs /src/debian /src/setup \
              /src/docker /src/k8s /src/scripts

FROM runtime AS final
ARG VCS_REF=unknown
ARG IMAGE_VERSION=dev
LABEL org.opencontainers.image.title="Odoo 16 Engine Base" \
      org.opencontainers.image.description="Extensible Odoo 16 Community runtime base image" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="LGPL-3.0-only"
WORKDIR /opt/odoo
COPY --from=source-pruner --chown=odoo:odoo /src /opt/odoo
COPY --from=frontend-builder --chown=odoo:odoo /src/managed/core/static/app /opt/odoo/managed/core/static/app
# Precompile immutable application code. Runtime still cannot write new bytecode.
RUN python -m compileall -q /opt/odoo

USER odoo
VOLUME ["/var/lib/odoo"]
EXPOSE 8069 8072
ENTRYPOINT ["/opt/odoo/odoo-bin"]
CMD ["--config=/etc/odoo/odoo.conf"]
