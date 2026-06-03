---
type: spec
project: stock-agent
phase: 05
tags: [spec, stock-agent, data]
created: "2026-05-17"
updated: "2026-05-28"
---

# Stock Agent Data Sources

## 数据源需求

| 工具 | 需要的数据 | 推荐数据源 |
|------|-----------|-----------|
| get_quote | 实时价格、涨跌幅、市值 | yfinance |
| get_kline | 历史价格、成交量 | yfinance |
| get_valuation | PE、PB、股息率 | yfinance |
| get_news | 股票相关新闻 | NewsAPI / yfinance news |

## 候选数据源评估

| 来源 | 支持市场 | 限制 | 成本 | 适合阶段 |
|------|---------|------|------|----------|
| **yfinance** | 美股、港股、A股 | 非官方API，可能被限速 | 免费 | 学习/原型 |
| Alpha Vantage | 美股为主 | 日限 25 次（免费） | 免费/付费 | 生产 |
| Tushare | A股 | 积分制，需要注册 | 免费/付费 | A股专用 |
| NewsAPI | 全球新闻 | 日限 100 次（免费） | 免费/付费 | 新闻检索 |

## 选定方案

学习阶段使用 yfinance 作为主要数据源，覆盖行情、K线、估值三个工具。

### 为什么选 yfinance
- **免费，不需要 API Key**，降低学习门槛
- **一个库覆盖 3 个工具**：get_quote、get_kline、get_valuation 都可以从 yfinance 获取
- **支持 A 股和美股**：可以直接对比茅台和苹果
- **Python 原生**：和 MCP server 无缝集成

### 新闻数据源
yfinance 自带 news 字段，可以获取基本新闻。如果需要更丰富的新闻，后期接入 NewsAPI。

## 工具与数据源映射

```python
# get_quote → yfinance
import yfinance as yf
ticker = yf.Ticker("AAPL")
info = ticker.info
# info['currentPrice'], info['marketCap'], info['volume']

# get_kline → yfinance
hist = ticker.history(period="1mo", interval="1d")
# hist['Close'], hist['Volume'] → 计算 MA, RSI, MACD

# get_valuation → yfinance
# info['trailingPE'], info['forwardPE'], info['priceToBook']
# info['dividendYield']

# get_news → yfinance
news = ticker.news
# [{'title': ..., 'publisher': ..., 'link': ...}]
```

## 认证方案

yfinance 不需要认证。如果后续接入 NewsAPI：
- API Key 存放在 .env 文件中
- MCP server 启动时读取环境变量
- 不硬编码在代码中

## 限速策略

| 数据源 | 限制 | 应对策略 |
|--------|------|----------|
| yfinance | 无官方限制，但高频可能被封 | 每次请求间隔 0.5 秒 |
| NewsAPI（未来） | 100 次/天 | 缓存新闻结果，同一股票 1 小时内不重复请求 |

## 数据流

```
用户输入 "茅台最近怎么样"
    ↓
Agent 决定调用 get_kline + get_news
    ↓
MCP server 接收请求
    ↓
get_kline → yfinance.Ticker("600519").history() → 计算指标 → 返回
get_news  → yfinance.Ticker("600519").news     → 格式化   → 返回
    ↓
Agent 收到两个工具的结果
    ↓
按日期对齐，输出带事件标注的趋势分析
```
