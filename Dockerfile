FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application
COPY . .

# Expose the runtime port
EXPOSE 8080

# Start AgentCore runtime
CMD ["uv", "run", "python", "agentcore_runtime.py"]