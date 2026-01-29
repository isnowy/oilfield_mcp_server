# 标准 MCP SSE Server 实现示例

# 1. 首先安装 MCP SDK (如果还没安装)
# pip install mcp

# 2. 创建标准的 MCP SSE server

import asyncio
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route

# 创建 MCP Server 实例
app_mcp = Server("oilfield-drilling")

# 注册你的 tools
@app_mcp.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_well_data",
            description="查询油井数据",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {"type": "string", "description": "井名"}
                },
                "required": ["well_name"]
            }
        )
    ]

@app_mcp.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "query_well_data":
        # 这里实现你的查询逻辑
        result = f"查询井 {arguments['well_name']} 的数据"
        return [TextContent(type="text", text=result)]
    
    raise ValueError(f"Unknown tool: {name}")

# 创建 SSE endpoint
async def handle_sse(request):
    async with SseServerTransport("/messages") as transport:
        await app_mcp.run(
            transport.read_stream,
            transport.write_stream,
            app_mcp.create_initialization_options()
        )

# 创建 Starlette app
starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse)
    ]
)

# 运行: uvicorn your_module:starlette_app --host 0.0.0.0 --port 8080
