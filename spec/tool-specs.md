---
type: spec
project: stock-agent
phase: 05
tags: [spec, stock-agent, tools]
created: "2026-05-17"
updated: "2026-05-28"
---

# Stock Agent Tool Specifications

> 选定 4 个工具：行情查询、K线分析、PE/PB查询、新闻检索。
> 工具通过 MCP 注册，SDK 自动发现。

## 工具总览

| # | 工具 | 状态 | 优先级 | 对应任务 |
|---|------|------|--------|----------|
| 1 | 行情查询 | ✅ 选定 | 核心 | 查行情、看趋势、全面分析、对比 |
| 2 | K线分析 | ✅ 选定 | 核心 | 看趋势、全面分析 |
| 3 | 市值查询 | ❌ 合并到行情 | — | — |
| 4 | PE/PB查询 | ✅ 选定 | 核心 | 全面分析、对比股票 |
| 5 | 持仓分析 | ❌ 留作扩展 | — | — |
| 6 | 新闻检索 | ✅ 选定 | 核心 | 看趋势、每日简报 |
| 7 | 价格预警 | ❌ 留作扩展 | — | — |

---

## MCP 注册方式

```python
# stock_server.py
from mcp.server import Server
from mcp.types import Tool

server = Server("stock-tools")

@server.tool()
def get_quote(symbol: str, market: str = "US") -> dict:
    """查询股票实时价格和涨跌幅"""
    ...

@server.tool()
def get_kline(symbol: str, indicators: list[str], period: str = "1mo", interval: str = "1d") -> dict:
    """计算技术指标（MA、RSI、MACD、布林带）"""
    ...

@server.tool()
def get_valuation(symbol: str, metrics: list[str] = ["PE", "PB"]) -> dict:
    """查询估值指标（市盈率、市净率、股息率）"""
    ...

@server.tool()
def get_news(symbol: str, keywords: list[str] = [], limit: int = 5, days: int = 7) -> dict:
    """检索股票相关新闻"""
    ...
```

对应的 mcpServers 配置：
```json
{
  "mcpServers": {
    "stock-tools": {
      "command": "python",
      "args": ["stock_server.py"]
    }
  }
}
```

SDK 启动时自动发现这 4 个工具，注册到 Agent Loop 中。

---

## Tool 1: get_quote — 行情查询

### Description
查询股票实时价格、涨跌幅、成交量等行情数据。返回值包含市值信息，不需要单独的市值查询工具。

### Parameters
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| symbol | string | Y | 股票代码（如 AAPL, 600519） |
| market | string | N | 市场（US, CN, HK），默认 US |

### Returns
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 189.84,
  "change": 1.23,
  "change_pct": 0.65,
  "volume": 52340000,
  "market_cap": 2950000000000,
  "currency": "USD",
  "timestamp": "2026-05-28T15:00:00Z"
}
```

### Errors
| Code | Description | Agent 行为 |
|------|-------------|-----------|
| SYMBOL_NOT_FOUND | 股票代码不存在 | 提示用户检查格式，举例：AAPL、600519 |
| DATA_UNAVAILABLE | 数据源暂时不可用 | 告知用户稍后重试 |
| MARKET_CLOSED | 市场已休市 | 返回最近数据，标注时间 |

### 对应任务
- 查行情："茅台现在多少钱" → 直接返回
- 对比股票：调用两次，对比结果
- 全面分析：作为综合报告的一部分

---

## Tool 2: get_kline — K线分析

### Description
计算技术指标，支持 MA、RSI、MACD、布林带。返回时间序列数据，Agent 可以和新闻按时间对齐。

### Parameters
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| symbol | string | Y | 股票代码 |
| indicators | list[str] | Y | 指标列表，如 ["MA", "RSI", "MACD"] |
| period | string | N | 时间周期（1mo, 3mo, 6mo, 1y），默认 1mo |
| interval | string | N | K线间隔（1d, 1wk, 1mo），默认 1d |

### Returns
```json
{
  "symbol": "AAPL",
  "data_points": 22,
  "dates": ["2026-05-01", "2026-05-02", ...],
  "close": [188.5, 189.0, 190.2, ...],
  "indicators": {
    "MA_20": [188.5, 189.0, ...],
    "RSI_14": [62.3, 61.8, ...],
    "MACD": {
      "macd": [1.2, 1.5, ...],
      "signal": [1.0, 1.1, ...],
      "histogram": [0.2, 0.4, ...]
    }
  }
}
```

返回 dates 数组，方便 Agent 和新闻按日期对齐。

### Errors
| Code | Description | Agent 行为 |
|------|-------------|-----------|
| SYMBOL_NOT_FOUND | 股票代码不存在 | 提示用户检查格式 |
| INVALID_INDICATOR | 不支持的指标 | 告知支持的指标：MA, RSI, MACD, BB |
| INSUFFICIENT_DATA | 数据点不足 | 用已有数据回答，标注数据范围 |

### 对应任务
- 看趋势："茅台最近一个月怎么样" → K线 + 新闻对齐
- 全面分析：作为综合报告的技术面部分

---

## Tool 3: get_valuation — PE/PB 查询

### Description
查询市盈率、市净率、股息率等估值指标，用于股票对比和全面分析。

### Parameters
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| symbol | string | Y | 股票代码 |
| metrics | list[str] | N | 指标列表，默认 ["PE", "PB", "PS", "dividend_yield"] |

### Returns
```json
{
  "symbol": "AAPL",
  "PE_TTM": 29.5,
  "PE_forward": 27.8,
  "PB": 45.2,
  "PS": 7.8,
  "dividend_yield": 0.52,
  "currency": "USD"
}
```

### Errors
| Code | Description | Agent 行为 |
|------|-------------|-----------|
| SYMBOL_NOT_FOUND | 股票代码不存在 | 提示用户检查格式 |
| DATA_UNAVAILABLE | 数据不可用 | 用已有数据回答，标注缺失指标 |

### 对应任务
- 对比股票："茅台和五粮液哪个估值更低" → 调用两次做对比表
- 全面分析：作为综合报告的估值部分

---

## Tool 4: get_news — 新闻检索

### Description
检索与股票相关的最新新闻，返回时间戳以便和 K 线数据对齐。

### Parameters
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| symbol | string | Y | 股票代码 |
| keywords | list[str] | N | 关键词过滤，默认不过滤 |
| limit | int | N | 返回条数，默认 5 |
| days | int | N | 最近 N 天，默认 7 |

### Returns
```json
{
  "news": [
    {
      "title": "Apple Reports Record Q1 Revenue",
      "source": "Reuters",
      "date": "2026-05-20",
      "summary": "Apple Inc reported...",
      "sentiment": "positive"
    }
  ],
  "total_count": 23
}
```

返回 date 字段，Agent 可以和 K 线的 dates 数组按日期对齐。

### Errors
| Code | Description | Agent 行为 |
|------|-------------|-----------|
| NO_NEWS_FOUND | 未找到相关新闻 | 告知用户近期无相关新闻 |
| DATA_UNAVAILABLE | 新闻数据源不可用 | 告知用户稍后重试 |

### 对应任务
- 看趋势：和 K 线按时间对齐，标注每个涨跌对应的事件
- 每日简报：并行查多只股票新闻，汇总市场简报
- 全面分析：作为综合报告的消息面部分

---

## 组合调用模式

Agent 的核心能力是**组合多个工具**，而不是单次调用：

### 趋势分析（看趋势）
```
用户: 茅台最近一个月怎么样
Agent:
  1. get_kline("600519", ["MA","RSI","MACD"], "1mo")
  2. get_news("600519", days=30)
  3. 按日期对齐，输出带事件标注的 K 线解读
```

### 全面分析
```
用户: 帮我分析一下 AAPL
Agent:
  1. get_quote("AAPL")
  2. get_kline("AAPL", ["MA","RSI","MACD"], "3mo")
  3. get_valuation("AAPL")
  4. get_news("AAPL", days=7)
  5. 输出综合报告：价格 + 技术面 + 估值 + 新闻面
```

### 每日简报
```
用户: 今天市场有什么重要消息
Agent:
  1. 并行调用 get_news(symbol, days=1) × N 只股票
  2. 汇总市场简报
```

---

## 设计原则
- 每个工具职责单一，不做"万能查询"
- 返回值包含足够上下文，让模型能直接解读（不需要额外解析）
- 错误码清晰，模型能根据错误决定重试还是拒答
- 返回时间序列数据（dates 数组），方便工具间按时间对齐
