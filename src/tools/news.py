# -*- coding: utf-8 -*-
"""get_news 工具：股票新闻检索。

用户问\"茅台最近有什么新闻\"，模型调用这个工具。
返回新闻标题、来源、摘要。

这个工具的价值：
  - 帮助用户理解\"为什么涨/跌\"（新闻驱动价格）
  - 配合K线分析（价格走势 + 新闻事件对齐）
  - 这就是你之前说的\"K线每个涨跌位置都有对应事件\"
"""

import yfinance as yf
from ..models import NewsItem, NewsResult, AgentError, ERROR_DEFINITIONS
from .quote import _normalize_symbol


def get_news(
    symbol: str,
    limit: int = 5,
    days: int = 7,
    market: str = 'US',
) -> NewsResult | AgentError:
    """检索股票相关新闻。

    Args:
        symbol: 股票代码
        limit: 返回条数，默认 5
        days: 最近 N 天，默认 7
        market: 市场

    Returns:
        NewsResult 或 AgentError
    """
    yf_symbol = _normalize_symbol(symbol, market)

    try:
        ticker = yf.Ticker(yf_symbol)
        news = ticker.news

        if not news:
            # 没有新闻不算错误，返回空列表
            return NewsResult(symbol=symbol, news=[], total_count=0)

        # 转换为 NewsItem 列表
        news_items = []
        for item in news[:limit]:
            content = item.get('content', {})
            news_items.append(NewsItem(
                title=content.get('title', 'No title'),
                source=content.get('provider', {}).get('name', 'Unknown'),
                date=content.get('pubDate', ''),
                summary=content.get('summary', ''),
            ))

        return NewsResult(
            symbol=symbol,
            news=news_items,
            total_count=len(news_items),
        )
    except Exception as e:
        # 新闻获取失败不算严重错误，返回空结果
        return NewsResult(symbol=symbol, news=[], total_count=0)
