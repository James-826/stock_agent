---
type: spec
project: stock-agent
phase: 05
tags: [spec, stock-agent, state]
created: "2026-05-17"
updated: "2026-05-28"
---

# Stock Agent State Design

## 为什么需要状态设计

Phase 3 学的 Session 机制告诉我们：Agent 需要记住用户之前看过什么股票、做过什么分析，才能在多轮对话中保持连贯。状态设计决定了 Agent "记什么"。

## State Schema（Pydantic）

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ToolResult(BaseModel):
    """单次工具调用的结果"""
    tool_name: str              # get_quote, get_kline 等
    symbol: str                 # 股票代码
    timestamp: datetime         # 调用时间
    data: dict                  # 工具返回的原始数据
    summary: str                # Agent 对结果的简要解读

class UserContext(BaseModel):
    """用户上下文，跨轮次保持"""
    watched_symbols: List[str] = []        # 用户关注的股票列表
    last_analyzed: Optional[str] = None    # 最后分析的股票
    analysis_history: List[ToolResult] = [] # 最近的工具调用记录

class StockAgentState(BaseModel):
    """Agent 完整状态"""
    session_id: str                          # 会话 ID
    user_context: UserContext                # 用户上下文
    current_symbol: Optional[str] = None    # 当前正在分析的股票
    tool_results_cache: dict = {}           # 本轮工具结果缓存
    created_at: datetime                     # 会话创建时间
    last_active: datetime                    # 最后活跃时间
```

## 状态字段说明

| 字段 | 类型 | 生命周期 | 说明 |
|------|------|---------|------|
| session_id | str | 会话级 | 对应 JSONL 文件路径 |
| watched_symbols | List[str] | 跨轮次 | 用户提过的股票，用于每日简报 |
| last_analyzed | Optional[str] | 跨轮次 | "帮我分析一下"时自动关联 |
| analysis_history | List[ToolResult] | 最近 N 条 | 避免重复调用相同工具 |
| current_symbol | Optional[str] | 单轮 | 当前轮次正在分析的股票 |
| tool_results_cache | dict | 单轮 | 同一轮内多工具结果的缓存 |

## 状态在 Agent Loop 中的变化

```
用户: "茅台现在多少钱"
    ↓
Agent Loop 开始
    ↓
1. 读取 state → watched_symbols: [], current_symbol: None
2. 模型决定调用 get_quote("600519")
3. 工具执行，返回结果
4. 更新 state:
   - current_symbol = "600519"
   - watched_symbols = ["600519"]
   - tool_results_cache["600519_quote"] = {...}
5. 模型生成回答
    ↓
Agent Loop 结束
6. 写入 JSONL（持久化）

---

用户: "帮我分析一下"
    ↓
Agent Loop 开始
    ↓
1. 读取 state → last_analyzed: "600519"
2. 模型理解 "帮我分析" = 分析 last_analyzed
3. 调用 get_kline + get_valuation + get_news（多工具并行）
4. 更新 state:
   - analysis_history.append(3个工具结果)
   - tool_results_cache 更新
5. 模型生成综合报告
    ↓
Agent Loop 结束
6. 写入 JSONL
```

## Session 持久化

对应 Phase 3 学的 JSONL 机制：

```
每次 Agent Loop 结束后：
    ↓
writeSessionJsonl(state)
    ↓
原子写入：.tmp → delete → rename
    ↓
JSONL 文件内容：
  line 1: {"role": "system", "content": "你是股票分析助手..."}
  line 2: {"role": "user", "content": "茅台现在多少钱"}
  line 3: {"role": "assistant", "content": "...", "tool_use": {...}}
  line 4: {"role": "tool", "content": "{price: 1680, ...}"}
  line 5: {"role": "user", "content": "帮我分析一下"}
  line 6: {"role": "assistant", "content": "..."}
```

**user_context（watched_symbols、last_analyzed）需要单独持久化**，因为它不是 messages 的一部分，而是从对话历史中提取的结构化信息。存放在 session header 中，用 readSessionHeader 快速加载。

## 与 Phase 3 知识的连接

| Phase 3 概念 | 在 Stock Agent 中的体现 |
|-------------|----------------------|
| Session（JSONL） | 对话历史持久化，崩溃恢复 |
| Session（SDK） | 自动拼接上下文，不需要手动管理 messages |
| Tool Cache | analysis_history 避免重复调用 |
| Context Trimming | 对话太长时，压缩早期工具结果 |
| parseMessagesResilient | 加载会话时跳过损坏行 |
