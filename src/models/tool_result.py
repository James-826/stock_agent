# -*- coding: utf-8 -*-
"""工具返回值的数据模型。

为什么要先定义这个？
  - 工具函数（Step 3）需要知道返回什么类型
  - Agent Loop（Step 6）需要检查返回值是成功还是错误
  - Session（Step 7）需要序列化存储

这就是 Phase 4 Data 层的作用：用 Pydantic 保证数据类型正确。
对应 oss 项目里 Zod 的 role。
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ============ 工具 1: get_quote 返回值 ============
# 用户问"茅台现在多少钱"，模型调用 stock_quote，返回这个结构

class QuoteResult(BaseModel):
    """实时行情结果"""
    symbol: str          # 股票代码，如 AAPL
    name: str            # 公司名称，如 Apple Inc.
    price: float         # 当前价格
    change: float        # 涨跌额（今天涨了多少美元）
    change_pct: float    # 涨跌幅（百分比）
    volume: int          # 成交量
    market_cap: Optional[float] = None  # 市值（可能没有）
    currency: str        # 货币单位，如 USD
    timestamp: datetime  # 查询时间


# ============ 工具 2: get_kline 返回值 ============
# 用户问"茅台最近一个月怎么样"，模型调用 stock_kline

class KlineResult(BaseModel):
    """K线 + 技术指标结果"""
    symbol: str
    data_points: int          # 数据点数量
    dates: list[str]          # 日期列表，如 ["2024-01-01", "2024-01-02", ...]
    close: list[float]        # 收盘价列表
    indicators: dict          # 技术指标，如 {"MA_20": [...], "RSI_14": [...]}


# ============ 工具 3: get_valuation 返回值 ============
# 用户问"茅台估值贵不贵"，模型调用 stock_valuation

class ValuationResult(BaseModel):
    """估值指标结果"""
    symbol: str
    pe_ttm: Optional[float] = None      # 市盈率（滚动）
    pe_forward: Optional[float] = None  # 市盈率（预期）
    pb: Optional[float] = None          # 市净率
    dividend_yield: Optional[float] = None  # 股息率
    currency: str = "USD"


# ============ 工具 4: get_news 返回值 ============
# 用户问"茅台最近有什么新闻"，模型调用 stock_news

class NewsItem(BaseModel):
    """单条新闻"""
    title: str        # 标题
    source: str       # 来源，如 Reuters
    date: str         # 日期
    summary: str      # 摘要


class NewsResult(BaseModel):
    """新闻检索结果"""
    symbol: str
    news: list[NewsItem]  # 新闻列表
    total_count: int       # 总条数
