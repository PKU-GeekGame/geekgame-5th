from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import mcp_client
from time import time

app = FastAPI()

# Simple rate limiter
rate_limit_timestamps = []
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit() -> bool:
    """Check if rate limit exceeded. Returns True if allowed, False if blocked."""
    global rate_limit_timestamps
    current_time = time()

    # Clean old timestamps outside the window
    rate_limit_timestamps = [
        ts for ts in rate_limit_timestamps
        if current_time - ts < RATE_LIMIT_WINDOW
    ]

    # Check if limit exceeded
    if len(rate_limit_timestamps) >= RATE_LIMIT_REQUESTS:
        return False

    # Add current timestamp
    rate_limit_timestamps.append(current_time)
    return True


class SampleRequest(BaseModel):
    query: str
    mcp_server: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EzMCP Client</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen py-8">
    <div class="container mx-auto max-w-2xl px-4">
        <div class="bg-white rounded-lg shadow-md p-6">
            <h1 class="text-2xl font-bold mb-6 text-gray-800">EzMCP Client</h1>

            <form id="taskForm" class="space-y-4">
                <div>
                    <label for="query" class="block text-sm font-medium text-gray-700 mb-2">Task Query</label>
                    <textarea
                        id="query"
                        name="query"
                        rows="3"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter your task here..."
                        required
                    ></textarea>
                </div>

                <div>
                    <label for="mcp_server" class="block text-sm font-medium text-gray-700 mb-2">MCP Server URL</label>
                    <input
                        type="text"
                        id="mcp_server"
                        name="mcp_server"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value="https://docs.mcp.cloudflare.com/mcp"
                        required
                    />
                </div>

                <button
                    type="submit"
                    class="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition duration-200"
                >
                    Execute Task
                </button>
            </form>

            <div id="loading" class="hidden mt-6 text-center">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <p class="mt-2 text-gray-600">Processing task...</p>
            </div>

            <div id="result" class="hidden mt-6">
                <h2 class="text-lg font-semibold mb-3 text-gray-800">Result</h2>
                <div id="resultContent" class="bg-gray-50 rounded-md p-4 border border-gray-200 whitespace-pre-wrap"></div>
            </div>

            <div id="error" class="hidden mt-6">
                <div class="bg-red-50 border border-red-200 rounded-md p-4">
                    <h2 class="text-lg font-semibold mb-2 text-red-800">Error</h2>
                    <p id="errorContent" class="text-red-700"></p>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('taskForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const query = document.getElementById('query').value;
            const mcp_server = document.getElementById('mcp_server').value;

            // Show loading, hide results/errors
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('result').classList.add('hidden');
            document.getElementById('error').classList.add('hidden');

            try {
                const response = await fetch('/sample', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query, mcp_server })
                });

                const data = await response.json();

                document.getElementById('loading').classList.add('hidden');

                if (response.ok) {
                    document.getElementById('resultContent').textContent = data.result;
                    document.getElementById('result').classList.remove('hidden');
                } else {
                    document.getElementById('errorContent').textContent = data.detail || 'An error occurred';
                    document.getElementById('error').classList.remove('hidden');
                }
            } catch (err) {
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('errorContent').textContent = err.message;
                document.getElementById('error').classList.remove('hidden');
            }
        });
    </script>
</body>
</html>
"""


@app.post("/sample")
async def sample(request: SampleRequest):
    # Check rate limit
    if not check_rate_limit():
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Maximum 5 requests per minute."
        )

    # Validate input parameters
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400, detail="Query parameter is required and cannot be empty"
        )

    if not request.mcp_server or not request.mcp_server.strip():
        raise HTTPException(
            status_code=400,
            detail="MCP server parameter is required and cannot be empty",
        )

    if not request.mcp_server.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, detail="MCP server must be a valid HTTP/HTTPS URL"
        )

    try:
        result = await mcp_client.agentic_sample(request.query, request.mcp_server)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing task: {str(e)}")


@app.post("/enable_builtin_tools")
async def enable_builtin_tools(request: Request):
    # Only accept localhost connections
    client_host = request.client.host if request.client else None
    print(f"[Web]:enable_builtin_tools\n  request.client: {request.client}")

    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=403, detail="Only localhost connections are allowed"
        )

    mcp_client.enable_builtin_tools = True
    return {"status": "success", "message": "Builtin tools enabled"}
