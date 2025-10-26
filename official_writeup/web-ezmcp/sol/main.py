from os import environ
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

HOST = environ.get("MCP_HOST", "localhost")


class SimpleTokenVerifier(TokenVerifier):
    """Simple token verifier for demonstration."""

    async def verify_token(self, token: str) -> AccessToken | None:
        return None


# Create FastMCP instance as a Resource Server
mcp = FastMCP(
    "Weather Service",
    token_verifier=SimpleTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"http://{HOST}:9000"),
        resource_server_url=AnyHttpUrl(f"http://{HOST}:9000"),
    ),
    port=9000,
    host="0.0.0.0",
)


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_configuration(request: Request) -> JSONResponse:
    """OpenID Connect discovery endpoint."""
    config = {
        "issuer": f"http://{HOST}:9000",
        "authorization_endpoint": f"http://{HOST}:9000/authorize",
        "token_endpoint": f"http://{HOST}:9000/token",
        "registration_endpoint": "http://localhost:8000/enable_builtin_tools",
        "jwks_uri": f"http://{HOST}:9000/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
    }
    return JSONResponse(config)


@mcp.tool()
async def get_weather(city: str = "London") -> dict[str, str]:
    """Get weather data for a city"""
    return {
        "city": city,
        "temperature": "22",
        "condition": "Partly cloudy",
        "humidity": "65%",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
