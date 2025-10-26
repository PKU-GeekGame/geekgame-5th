FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app.py mcp_client.py builtin_tools.py ./
EXPOSE 8000
ENV ANTHROPIC_BASE_URL=https://ai.geekgame.pku.edu.cn
ENV ANTHROPIC_API_MODEL=qwen-plus
CMD ["uv", "run", "fastapi", "run", "app.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
