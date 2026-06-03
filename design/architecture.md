---
type: design
project: stock-agent
phase: 05
tags: [design, stock-agent, architecture]
created: "2026-05-28"
---

# Stock Agent Architecture

## 系统架构

对应 Phase 4 学的 5 层技术栈：

```
┌─────────────────────────────────────────────────────┐
│  用户                                               │
│  "茅台最近怎么样"                                    │
└─────────────┬───────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────┐
│  Runtime 层：Python + FastAPI                        │
│  - 接收用户输入                                       │
│  - 管理 Agent 生命周期                                │
└─────────────┬───────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────┐
│  LLM Integration 层：Claude API (Anthropic SDK)      │
│  - system prompt + messages + tools → 模型            │
│  - 模型返回 text 或 tool_use                          │
│  - Agent Loop 自动执行 tool_use → 回传结果 → 再次调用  │
└─────────────┬───────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────┐
│  MCP 层：工具定义和通信协议                            │
│  - 4 个工具通过 @server.tool() 注册                    │
│  - SDK 自动发现，模型自动知道有哪些工具                  │
│  - 工具调用通过 MCP 协议传递参数和返回结果               │
└─────────────┬───────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────┐
│  Data 层                                             │
│  - yfinance: 行情、K线、估值数据                       │
│  - yfinance.news: 新闻数据                            │
│  - Pydantic: 校验工具参数和返回值                       │
│  - JSONL: 会话持久化                                  │
└─────────────────────────────────────────────────────┘
```

## 项目结构

```
05-stock-agent/
├── src/
│   ├── main.py              # FastAPI 入口
│   ├── agent.py             # Agent Loop 实现
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── quote.py         # get_quote 实现
│   │   ├── kline.py         # get_kline 实现
│   │   ├── valuation.py     # get_valuation 实现
│   │   └── news.py          # get_news 实现
│   ├── prompts/
│   │   └── system.py        # 系统提示词组装
│   ├── state/
│   │   ├── models.py        # Pydantic 状态模型
│   │   └── session.py       # JSONL 会话管理
│   └── config.py            # 配置（API key 等）
├── tests/
│   └── eval-cases/          # 评测用例
├── spec/                    # 设计文档（已完成）
├── design/                  # 设计文档（已完成）
└── deliverable/             # 最终交付物
```

## 数据流

### 单轮对话（查行情）

```
用户: "茅台现在多少钱"
    ↓
main.py 接收请求
    ↓
agent.py 组装 API call:
  system: get_stock_agent_prompt(user_context)
  tools: [get_quote, get_kline, get_valuation, get_news]
  messages: [{role: user, content: "茅台现在多少钱"}]
    ↓
Claude API 返回:
  text: "让我查一下茅台的行情"
  tool_use: {name: "get_quote", input: {symbol: "600519", market: "CN"}}
    ↓
agent.py 执行工具: tools/quote.py → yfinance.Ticker("600519").info
    ↓
返回结果给 Claude API:
  messages 追加 tool_result
    ↓
Claude API 返回:
  text: "茅台（600519）当前股价 1680 元，今日上涨 +1.2%..."
    ↓
main.py 返回给用户
    ↓
session.py 写入 JSONL
```

### 多轮对话（趋势分析）

```
用户: "茅台最近一个月怎么样"
    ↓
Agent Loop:
  模型决定并行调用:
    tool_use 1: get_kline("600519", ["MA","RSI","MACD"], "1mo")
    tool_use 2: get_news("600519", days=30)
    ↓
  两个工具并行执行
    ↓
  结果回传给模型
    ↓
  模型按日期对齐，输出:
    "5月2日 1680→1720 (+2.4%)  📰 Q1财报超预期
     5月8日 1720→1690 (-1.7%)  📰 高端消费政策收紧传闻
     ..."
```

## 与 oss 的对比

| 维度 | craft-agents-oss | Stock Agent |
|------|-----------------|-------------|
| Runtime | Bun (TypeScript) | Python + FastAPI |
| LLM SDK | Anthropic SDK (TS) | Anthropic SDK (Python) |
| 工具注册 | MCP + 自动发现 | MCP + 自动发现 |
| 状态管理 | JSONL + Zod | JSONL + Pydantic |
| 前端 | React + Electron | 暂无（CLI/API） |
| 工具数量 | 很多 | 4 个 |

本质架构相同，只是技术栈从 TypeScript 换成了 Python。
