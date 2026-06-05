# -*- coding: utf-8 -*-
"""get_valuation 工具：估值指标查询。

用户问\"茅台估值贵不贵\"，模型调用这个工具。
返回 PE、PB、股息率等估值指标。

这就是巴菲特看的那些指标：
  - PE（市盈率）：股价 / 每股收益，越低越便宜
  - PB（市净率）：股价 / 每股净资产，越低越便宜
  - 股息率：每股分红 / 股价，越高越好
"""

import yfinance as yf
from ..models import ValuationResult, AgentError, ERROR_DEFINITIONS
from .quote import _normalize_symbol


def get_valuation(symbol: str, market: str = 'US') -> ValuationResult | AgentError:
    """查询股票估值指标。

    Args:
        symbol: 股票代码
        market: 市场

    Returns:
        ValuationResult 或 AgentError
    """
    yf_symbol = _normalize_symbol(symbol, market)

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info:
            return ERROR_DEFINITIONS['SYMBOL_NOT_FOUND']

        return ValuationResult(
            symbol=symbol,
            pe_ttm=info.get('trailingPE'),           # 滚动市盈率（过去12个月）
            pe_forward=info.get('forwardPE'),         # 预期市盈率（未来12个月）
            pb=info.get('priceToBook'),               # 市净率
            dividend_yield=info.get('dividendYield'), # 股息率（小数，如 0.02 = 2%）
            currency=info.get('currency', 'USD'),
        )
    except Exception as e:
        if 'No data found' in str(e):
            return ERROR_DEFINITIONS['SYMBOL_NOT_FOUND']
        return ERROR_DEFINITIONS['DATA_UNAVAILABLE']
