FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
  iproute2 procps vim nano curl wget lrzsz \
  && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN uv init --vcs=none
RUN uv add "mcp[cli]"
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["su", "-P", "-l", "-c", "/entrypoint.sh"]
