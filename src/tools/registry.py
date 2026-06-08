# -*- coding: utf-8 -*-
"""Tool Registry

Phase 3 learned MCP tool registration mechanism:
- Tools need name, description, parameters
- These are sent to Claude API in JSON Schema format
- Model sees tool descriptions and decides when to call which tool

We manually define JSON Schema (Step 4 is manual first, can later change to MCP auto-generation)

Corresponding to oss project:
- claude-agent.ts: tools: { type: 'preset', preset: 'claude_code' }
- MCP server returns tool list
"""

from .quote import get_quote
from .kline import get_kline
from .valuation import get_valuation
from .news import get_news
from .trend_tool import analyze_stock_trend
from ..models import AgentError

import json


# Tool name -> function mapping
# Agent Loop parses tool_use, finds corresponding function here to execute
TOOL_REGISTRY = {
    'stock_quote': get_quote,
    'stock_kline': get_kline,
    'stock_valuation': get_valuation,
    'stock_news': get_news,
    'analyze_trend': analyze_stock_trend,
}

# Claude API tools parameter format (JSON Schema)
# This tells the model: what tools you have
# Model sees these descriptions and decides when to call which tool
TOOL_DEFINITIONS = [
    {
        'name': 'stock_quote',
        'description': 'Query real-time stock price and change. Use case: user asks "How much is NVDA now?", "Did AAPL go up today?"',
        'input_schema': {
            'type': 'object',
            'properties': {
                'symbol': {
                    'type': 'string',
                    'description': 'Stock code, e.g. NVDA, 600519'
                },
                'market': {
                    'type': 'string',
                    'enum': ['US', 'CN', 'HK'],
                    'description': 'Market, default US'
                },
            },
            'required': ['symbol'],
        },
    },
    {
        'name': 'stock_kline',
        'description': 'Calculate technical indicators (MA, RSI, MACD, Bollinger Bands). Use case: user asks "How is NVDA recently?", "What is AAPL\'s RSI?"',
        'input_schema': {
            'type': 'object',
            'properties': {
                'symbol': {
                    'type': 'string',
                    'description': 'Stock code'
                },
                'indicators': {
                    'type': 'array',
                    'items': {'type': 'string', 'enum': ['MA', 'RSI', 'MACD', 'BB']},
                    'description': 'Indicator list'
                },
                'period': {
                    'type': 'string',
                    'enum': ['1mo', '3mo', '6mo', '1y'],
                    'description': 'Time period, default 1mo'
                },
                'interval': {
                    'type': 'string',
                    'enum': ['1d', '1wk', '1mo'],
                    'description': 'K-line interval, default 1d'
                },
                'market': {
                    'type': 'string',
                    'enum': ['US', 'CN', 'HK'],
                    'description': 'Market, default US'
                },
            },
            'required': ['symbol', 'indicators'],
        },
    },
    {
        'name': 'stock_valuation',
        'description': 'Query valuation metrics (PE, PB, dividend yield). Use case: user asks "Is NVDA expensive?", "What is AAPL\'s PE?"',
        'input_schema': {
            'type': 'object',
            'properties': {
                'symbol': {
                    'type': 'string',
                    'description': 'Stock code'
                },
                'market': {
                    'type': 'string',
                    'enum': ['US', 'CN', 'HK'],
                    'description': 'Market, default US'
                },
            },
            'required': ['symbol'],
        },
    },
    {
        'name': 'stock_news',
        'description': 'Search for stock-related news. Use case: user asks "What\'s the latest NVDA news?", "Why did AAPL go up today?"',
        'input_schema': {
            'type': 'object',
            'properties': {
                'symbol': {
                    'type': 'string',
                    'description': 'Stock code'
                },
                'limit': {
                    'type': 'integer',
                    'description': 'Number of results, default 5'
                },
                'days': {
                    'type': 'integer',
                    'description': 'Last N days, default 7'
                },
                'market': {
                    'type': 'string',
                    'enum': ['US', 'CN', 'HK'],
                    'description': 'Market, default US'
                },
            },
            'required': ['symbol'],
        },
    },
    {
        'name': 'analyze_trend',
        'description': 'Comprehensive trend analysis combining MA, MACD, RSI, Bollinger Bands, VIX, and valuation metrics. Returns buy/sell score (0-100). Use case: user asks "Analyze NVDA trend", "Should I buy AAPL?", "Give me a comprehensive analysis of TSLA"',
        'input_schema': {
            'type': 'object',
            'properties': {
                'symbol': {
                    'type': 'string',
                    'description': 'Stock code, e.g. NVDA, AAPL'
                },
                'period': {
                    'type': 'string',
                    'enum': ['1mo', '3mo', '6mo', '1y'],
                    'description': 'Time period for analysis, default 3mo'
                },
                'market': {
                    'type': 'string',
                    'enum': ['US', 'CN', 'HK'],
                    'description': 'Market, default US'
                },
            },
            'required': ['symbol'],
        },
    },
]


def execute_tool(name: str, params: dict) -> str:
    """Execute tool call, return JSON string.

    Corresponding to Phase 3 tool call flow:
      1. Find tool function from TOOL_REGISTRY
      2. Execute with parameters
      3. If return AgentError, format error info
      4. If return Pydantic model, serialize to JSON
    """
    func = TOOL_REGISTRY.get(name)
    if not func:
        return json.dumps({'error': 'UNKNOWN_TOOL', 'message': f'Unknown tool: {name}'})

    try:
        result = func(**params)
        if isinstance(result, AgentError):
            return json.dumps({
                'error': result.code,
                'title': result.title,
                'message': result.message,
                'can_retry': result.can_retry,
            }, ensure_ascii=False)
        return json.dumps(result, ensure_ascii=False, default=str)
    except TypeError as e:
        return json.dumps({'error': 'INVALID_PARAMS', 'message': f'Parameter error: {e}'})
    except Exception as e:
        return json.dumps({'error': 'EXECUTION_ERROR', 'message': f'Execution failed: {e}'})
