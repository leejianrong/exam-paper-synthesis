# Production image (W4): the API serving the built web app on one origin.
#   docker build -t exam-paper-synthesis .
#   docker run --env-file prod.env -p 8080:8080 exam-paper-synthesis
# Needs the environment in docs/LAUNCH.md (EXAM_ENV=production refuses to boot without it).

FROM node:24-slim AS web
WORKDIR /src
COPY package.json package-lock.json ./
COPY web/package.json web/package-lock.json web/
RUN npm --prefix web ci
COPY web web
# Same origin as the API: relative URLs, no CORS, first-party cookies.
ENV VITE_API=""
RUN npm --prefix web run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    EXAM_ENV=production EXAM_CHROMIUM_NO_SANDBOX=1 \
    EXAM_WEB_DIST=/app/web-dist
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY engine engine
COPY api api
COPY cli cli
RUN uv sync --frozen --no-dev --package exam-api \
 && uv run --no-sync playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*
COPY --from=web /src/web/dist /app/web-dist
RUN useradd --create-home --uid 10001 app && chown -R app /app /opt/pw-browsers
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
