# syntax=docker/dockerfile:1.10
# ---- build stage: install dependencies into a virtual environment ----
FROM python:3.12-slim-bookworm AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY app/requirements.txt .
RUN python -m venv /venv && /venv/bin/pip install -r requirements.txt

# ---- runtime stage: small image, no compilers, no pip, non-root ----
FROM python:3.12-slim-bookworm AS runtime
LABEL org.opencontainers.image.title="shop-api" \
      org.opencontainers.image.source="https://github.com/s0sta/secure-delivery-pipeline" \
      org.opencontainers.image.licenses="MIT"
ENV PATH="/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=prod
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip* /usr/local/bin/pip*
COPY --from=build /venv /venv
COPY --chown=10001:10001 app /srv/app
WORKDIR /srv
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"]
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-server-header", "--proxy-headers"]
