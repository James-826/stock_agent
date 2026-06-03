"""工具注册表。

Phase 3 学的 MCP 自动发现机制，在 Claude API 的 Python SDK 中，
工具是通过 tools 参数传给 API 的 JSON Schema 列表。
这里我们手动定义工具的 JSON Schema（因为不通过 MCP server 运行时）。

如果通过 MCP server 运行，SDK 会自动从 MCP server 发现这些工具定义。
"""

from ..tools.quote import get_quote
from ..tools.kline import get_kline
from ..tools.valuation import get_valuation
from ..tools.news import get_news
from ..models import AgentError

import json


# 工具名 → 函数的映射
TOOL_REGISTRY = {
    "stock_quote": get_quote,
    "stock_kline": get_kline,
    "stock_valuation": get_valuation,
    "stock_news": get_news,
}

# Claude API 的 tools 参数格式（JSON Schema）
# 这告诉模型"你有哪些工具可以用"
TOOL_DEFINITIONS = [
    {
        "name": "stock_quote",
        "description": "查询股票实时价格和涨跌幅。使用场景：用户问'茅台现在多少钱'、'AAPL今天涨了吗'",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 AAPL、600519"
                },
                "market": {
                    "type": "string",
                    "enum": ["US", "CN", "HK"],
                    "description": "市场，默认 US"
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "stock_kline",
        "description": "计算技术指标（MA、RSI、MACD、布林带）。使用场景：用户问'茅台最近怎么样'、'AAPL的RSI是多少'",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "indicators": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["MA", "RSI", "MACD", "BB"]},
                    "description": "指标列表"
                },
                "period": {
                    "type": "string",
                    "enum": ["1mo", "3mo", "6mo", "1y"],
                    "description": "时间周期，默认 1mo"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1d", "1wk", "1mo"],
                    "description": "K线间隔，默认 1d"
                },
                "market": {
                    "type": "string",
                    "enum": ["US", "CN", "HK"],
                    "description": "市场，默认 US"
                },
            },
            "required": ["symbol", "indicators"],
        },
    },
    {
        "name": "stock_valuation",
        "description": "查询估值指标（PE、PB、股息率）。使用场景：用户问'茅台估值贵不贵'、'AAPL的PE是多少'",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "market": {
                    "type": "string",
                    "enum": ["US", "CN", "HK"],
                    "description": "市场，默认 US"
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "stock_news",
        "description": "检索股票相关新闻。使用场景：用户问'茅台最近有什么新闻'、'AAPL今天为什么涨了'",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键词过滤"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 5"
                },
                "days": {
                    "type": "integer",
                    "description": "最近 N 天，默认 7"
                },
                "market": {
                    "type": "string",
                    "enum": ["US", "CN", "HK"],
                    "description": "市场，默认 US"
                },
            },
            "required": ["symbol"],
        },
    },
]


def execute_tool(name: str, params: dict) -> str:
    """执行工具调用，返回 JSON 字符串。

    对应 Phase 3 学的工具调用流程：
    1. 从 TOOL_REGISTRY 找到工具函数
    2. 传入参数执行
    3. 如果返回 AgentError，格式化错误信息
    4. 如果返回 Pydantic 模型，序列化为 JSON
    """
    func = TOOL_REGISTRY.get(name)
    if not func:
        return json.dumps({"error": "UNKNOWN_TOOL", "message": f"未知工具: {name}"})

    try:
        result = func(**params)
        if isinstance(result, AgentError):
            return json.dumps({
                "error": result.code,
                "title": result.title,
                "message": result.message,
                "can_retry": result.can_retry,
            }, ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False, default=str)
    except TypeError as e:
        return json.dumps({"error": "INVALID_PARAMS", "message": f"参数错误: {e}"})
    except Exception as e:
        return json.dumps({"error": "EXECUTION_ERROR", "message": f"执行失败: {e}"})
