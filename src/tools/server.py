"""MCP Server：把 4 个工具注册到 MCP 协议中。

对应 Phase 3 学的 MCP 机制：
- @server.tool() 装饰器自动注册工具
- SDK 启动时自动发现这些工具
- 工具的 docstring 就是模型看到的工具描述
- 参数的类型注解就是模型看到的参数定义

运行方式：
    python -m tools.server
    或者在 mcpServers 配置中指定这个文件
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
import json

from .quote import get_quote
from .kline import get_kline
from .valuation import get_valuation
from .news import get_news
from ..models import AgentError

server = Server("stock-tools")


def _format_result(result) -> str:
    """将工具返回值格式化为 JSON 字符串。

    如果是 AgentError，返回错误信息。
    如果是 Pydantic 模型，返回 JSON。
    """
    if isinstance(result, AgentError):
        return json.dumps({
            "error": result.code,
            "title": result.title,
            "message": result.message,
            "can_retry": result.can_retry,
        }, ensure_ascii=False)

    # Pydantic 模型 → dict → JSON
    return json.dumps(result.model_dump(), ensure_ascii=False, default=str)


@server.tool()
def stock_quote(symbol: str, market: str = "US") -> str:
    """查询股票实时价格和涨跌幅。

    使用场景：用户问"茅台现在多少钱"、"AAPL 今天涨了吗"
    """
    result = get_quote(symbol, market)
    return _format_result(result)


@server.tool()
def stock_kline(
    symbol: str,
    indicators: list[str],
    period: str = "1mo",
    interval: str = "1d",
    market: str = "US",
) -> str:
    """计算技术指标（MA、RSI、MACD、布林带）。

    使用场景：用户问"茅台最近一个月怎么样"、"AAPL 的 RSI 是多少"
    """
    result = get_kline(symbol, indicators, period, interval, market)
    return _format_result(result)


@server.tool()
def stock_valuation(
    symbol: str,
    metrics: list[str] | None = None,
    market: str = "US",
) -> str:
    """查询估值指标（PE、PB、股息率）。

    使用场景：用户问"茅台估值贵不贵"、"AAPL 的 PE 是多少"
    """
    result = get_valuation(symbol, metrics, market)
    return _format_result(result)


@server.tool()
def stock_news(
    symbol: str,
    keywords: list[str] | None = None,
    limit: int = 5,
    days: int = 7,
    market: str = "US",
) -> str:
    """检索股票相关新闻。

    使用场景：用户问"茅台最近有什么新闻"、"AAPL 今天为什么涨了"
    """
    result = get_news(symbol, keywords, limit, days, market)
    return _format_result(result)


async def run_server():
    """启动 MCP server（通过 stdio 通信）"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server())
