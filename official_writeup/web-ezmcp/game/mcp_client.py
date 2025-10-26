from os import environ
from time import time
from typing import List, cast
from pydantic import AnyUrl
import anthropic

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
import builtin_tools


class InMemoryTokenStorage(TokenStorage):
    def __init__(self):
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info


async def handle_redirect(auth_url: str) -> None:
    print(f"mcp_client:[handle_redirect] auth_url={auth_url}")


async def handle_callback() -> tuple[str, str | None]:
    code, state = "example_code", "example_state"
    print(f"mcp_client:[handle_callback] using mock data code={code} state={state}")
    return code, state


enable_builtin_tools = False


async def agentic_sample(query: str, mcp_server: str) -> str:
    print(f"start agentic sample with mcp: {mcp_server}\nquery: {query}")
    oauth_auth = OAuthClientProvider(
        server_url="",
        client_metadata=OAuthClientMetadata(
            client_name="EzMCP Client",
            redirect_uris=[AnyUrl("http://localhost:3000/callback")],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="user",
        ),
        storage=InMemoryTokenStorage(),
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )
    start = time()

    async with streamablehttp_client(mcp_server, auth=oauth_auth) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"Session initialized in {time() - start:.2f} seconds")

            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")

            anthropic_tools = []
            for tool in tools.tools:
                anthropic_tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                    }
                )

            if enable_builtin_tools:
                anthropic_tools.extend(
                    [
                        {
                            "name": "system",
                            "description": "Execute a system command with the given parameters",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "cmd": {
                                        "type": "string",
                                        "description": "Command to execute",
                                    },
                                    "params": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Command parameters",
                                    },
                                },
                                "required": ["cmd", "params"],
                            },
                        },
                        {
                            "name": "eval",
                            "description": "Evaluate a Python expression with the given variables",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Python code to evaluate",
                                    },
                                    "variables": {
                                        "type": "object",
                                        "description": "Variables to use in the evaluation",
                                    },
                                },
                                "required": ["code", "variables"],
                            },
                        },
                    ]
                )
                print("Added builtin tools: system, eval")

            client = anthropic.Anthropic()
            model = environ.get("ANTHROPIC_API_MODEL", "claude-sonnet-4-5-20250929")
            print(f"Using model: {model}")
            messages: List[anthropic.types.MessageParam] = [
                {"role": "user", "content": query}
            ]
            iteration_limit = 5
            for iteration in range(iteration_limit):
                use_tools = iteration < iteration_limit - 1
                print(f"\n--- Iteration {iteration + 1} ---")
                start = time()
                if use_tools and anthropic_tools:
                    response = client.messages.create(
                        model=model,
                        max_tokens=4096,
                        messages=messages,
                        tools=anthropic_tools,
                        temperature=0,
                    )
                else:
                    response = client.messages.create(
                        model=model,
                        max_tokens=4096,
                        messages=messages,
                        temperature=0,
                    )
                print(f"Response time: {time() - start:.2f} seconds")

                has_tool_use = any(
                    block.type == "tool_use" for block in response.content
                )

                if not has_tool_use:
                    text_content = ""
                    for block in response.content:
                        if block.type == "text":
                            text_content += block.text
                    return text_content

                assistant_content = []
                tool_results: List[anthropic.types.ToolResultBlockParam] = []

                for block in response.content:
                    print(f"Received block: {block.type}")
                    assistant_content.append(block)

                    if block.type == "tool_use":
                        print(f"Calling tool: {block.name} with input: {block.input}")

                        # Check if it's a builtin tool
                        if enable_builtin_tools and block.name in ["system", "eval"]:
                            try:
                                tool_input = cast(dict, block.input)
                                result_text = ""
                                if block.name == "system":
                                    result_text = builtin_tools.system(
                                        tool_input["cmd"], tool_input["params"]
                                    )
                                elif block.name == "eval":
                                    result_text = builtin_tools.eval(
                                        tool_input["code"], tool_input["variables"]
                                    )

                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": [
                                            {"type": "text", "text": result_text}
                                        ],
                                    }
                                )
                            except Exception as e:
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": [
                                            {"type": "text", "text": f"Error: {str(e)}"}
                                        ],
                                        "is_error": True,
                                    }
                                )
                        else:
                            # Call the MCP tool
                            result = await session.call_tool(
                                block.name, cast(dict, block.input)
                            )

                            # Extract result content (only text blocks for simplicity)
                            result_content: List[anthropic.types.TextBlockParam] = []
                            for res_block in result.content:
                                if res_block.type == "text":
                                    result_content.append(
                                        {
                                            "type": "text",
                                            "text": res_block.text,
                                        }
                                    )

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result_content,
                                }
                            )

                # Add assistant message and tool results to conversation
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

            # If we've exhausted iterations, return the last response
            return "Maximum iterations reached without final answer"
