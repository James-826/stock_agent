# -*- coding: utf-8 -*-
"""get_quote 工具：查询股票实时价格。

数据来源：yfinance（雅虎财经 Python 库）
返回值：QuoteResult 或 AgentError

对应 Phase 3 学的工具定义：
  - 工具职责单一：只查价格，不查估值、不查新闻
  - 返回值包含足够上下文，模型能直接理解
  - 错误码清晰，模型能根据错误决定重试还是提示用户
"""

import yfinance as yf
from datetime import datetime
from ..models import QuoteResult, AgentError, ERROR_DEFINITIONS


def get_quote(symbol: str, market: str = 'US') -> QuoteResult | AgentError:
    """查询股票实时价格和涨跌幅。

    Args:
        symbol: 股票代码，如 AAPL、600519
        market: 市场（US、CN、HK），用于格式化代码

    Returns:
        QuoteResult 或 AgentError
    """
    # A股代码格式转换：600519 -> 600519.SS（上交所）、000858 -> 000858.SZ（深交所）
    yf_symbol = _normalize_symbol(symbol, market)

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        # yfinance 返回 {} 表示代码不存在
        if not info or 'currentPrice' not in info:
            return ERROR_DEFINITIONS['SYMBOL_NOT_FOUND']

        return QuoteResult(
            symbol=symbol,
            name=info.get('shortName', info.get('longName', symbol)),
            price=info['currentPrice'],
            change=info.get('currentPrice', 0) - info.get('previousClose', info.get('currentPrice', 0)),
            change_pct=info.get('regularMarketChangePercent', 0),
            volume=info.get('volume', 0),
            market_cap=info.get('marketCap'),
            currency=info.get('currency', 'USD'),
            timestamp=datetime.now(),
        )
    except Exception as e:
        if 'No data found' in str(e):
            return ERROR_DEFINITIONS['SYMBOL_NOT_FOUND']
        return ERROR_DEFINITIONS['DATA_UNAVAILABLE']


def _normalize_symbol(symbol: str, market: str) -> str:
    """将用户输入的代码转换为 yfinance 格式。

    用户输入: AAPL、600519、000858
    yfinance: AAPL、600519.SS、000858.SZ
    """
    if market == 'US':
        return symbol.upper()

    if market == 'CN':
        code = symbol.strip()
        if code.startswith('6'):
            return f'{code}.SS'  # 上交所
        else:
            return f'{code}.SZ'  # 深交所

    if market == 'HK':
        return f'{symbol}.HK'

    return symbol
