---
type: design
project: stock-agent
phase: 05
tags: [design, stock-agent, error-handling]
created: "2026-05-28"
---

# Stock Agent Error Handling Strategy

## 错误处理原则

对应 Phase 3 学的 oss 错误处理架构：typed error codes + 4 条恢复路径

## 错误码定义

```python
from pydantic import BaseModel
from typing import List, Optional

class RecoveryAction(BaseModel):
    label: str          # 用户看到的操作名
    action: str         # 执行的操作

class AgentError(BaseModel):
    code: str           # 错误码
    title: str          # 用户看到的标题
    message: str        # 用户看到的详细说明
    actions: List[RecoveryAction]  # 建议操作
    can_retry: bool     # 是否可重试
    retry_delay_ms: Optional[int] = None  # 重试间隔

ERROR_DEFINITIONS = {
    "SYMBOL_NOT_FOUND": AgentError(
        code="SYMBOL_NOT_FOUND",
        title="股票代码不存在",
        message="未找到该股票代码，请检查格式。美股示例：AAPL，A股示例：600519",
        actions=[RecoveryAction(label="检查代码格式", action="show_help")],
        can_retry=False,
    ),
    "DATA_UNAVAILABLE": AgentError(
        code="DATA_UNAVAILABLE",
        title="数据源暂时不可用",
        message="股票数据源当前无法访问，请稍后重试",
        actions=[RecoveryAction(label="重试", action="retry")],
        can_retry=True,
        retry_delay_ms=5000,
    ),
    "MARKET_CLOSED": AgentError(
        code="MARKET_CLOSED",
        title="市场已休市",
        message="当前市场已休市，返回最近可用数据",
        actions=[],
        can_retry=False,
    ),
    "INVALID_INDICATOR": AgentError(
        code="INVALID_INDICATOR",
        title="不支持的指标类型",
        message="当前支持的指标：MA、RSI、MACD、BB（布林带）",
        actions=[RecoveryAction(label="查看支持列表", action="show_indicators")],
        can_retry=False,
    ),
    "INSUFFICIENT_DATA": AgentError(
        code="INSUFFICIENT_DATA",
        title="数据点不足",
        message="历史数据不足以计算所请求的指标，将使用可用数据",
        actions=[],
        can_retry=False,
    ),
    "NO_NEWS_FOUND": AgentError(
        code="NO_NEWS_FOUND",
        title="未找到相关新闻",
        message="近期没有找到该股票的相关新闻",
        actions=[RecoveryAction(label="扩大时间范围", action="increase_days")],
        can_retry=False,
    ),
    "TIMEOUT": AgentError(
        code="TIMEOUT",
        title="请求超时",
        message="数据源响应超时，正在重试...",
        actions=[RecoveryAction(label="重试", action="retry")],
        can_retry=True,
        retry_delay_ms=3000,
    ),
}
```

## 4 条恢复路径

对应 Phase 3 学的 oss catch block 的 4 条路径：

```python
async def handle_tool_error(error: AgentError, retry_count: int = 0) -> str:
    """工具调用失败时的恢复策略"""

    # 路径 1: 可重试错误 → 自动重试
    if error.can_retry and retry_count < 1:
        await asyncio.sleep(error.retry_delay_ms / 1000)
        return await retry_tool_call()

    # 路径 2: 参数错误 → 提示用户修正
    if error.code in ["SYMBOL_NOT_FOUND", "INVALID_INDICATOR"]:
        return format_user_friendly_error(error)

    # 路径 3: 数据不完整 → 用已有数据回答
    if error.code in ["INSUFFICIENT_DATA", "MARKET_CLOSED"]:
        return format_partial_data_response(error)

    # 路径 4: 不可恢复错误 → 告知用户
    return format_unrecoverable_error(error)
```

## 每个错误的 Agent 行为

| 错误码 | 恢复路径 | Agent 对用户说什么 |
|--------|---------|-------------------|
| SYMBOL_NOT_FOUND | 路径 2 | "未找到股票代码 'XXX'。美股请用 ticker 如 AAPL，A股请用代码如 600519" |
| DATA_UNAVAILABLE | 路径 1→4 | 先重试一次，仍失败则 "数据源暂时不可用，请稍后再试" |
| MARKET_CLOSED | 路径 3 | "当前美股已休市，以下数据截至北京时间 XX:XX" |
| INVALID_INDICATOR | 路径 2 | "不支持指标 'XXX'，目前支持：MA、RSI、MACD、布林带" |
| INSUFFICIENT_DATA | 路径 3 | "历史数据不足，以下分析基于最近 N 天数据" |
| NO_NEWS_FOUND | 路径 2 | "近期没有找到相关新闻，是否需要扩大时间范围？" |
| TIMEOUT | 路径 1→4 | 先自动重试，仍超时则 "请求超时，请稍后再试" |

## 用户确认机制

本 Agent 是只读型，不执行写入操作，因此不需要用户确认。

对应 Phase 3 学的两层权限控制：
- **系统提示词（软控制）**：告诉模型"你不能预测股价、不能执行交易"
- **工具层面（硬控制）**：4 个工具全是读取操作，没有写入工具

未来如果扩展为交易型 Agent，需要在 PreToolUse hook 中加入用户确认：
```python
# 未来扩展：交易确认
if tool_name in ["buy_stock", "sell_stock"]:
    require_user_confirmation(
        f"确认执行 {tool_name}({params})？"
    )
```

## 错误日志

```python
import logging

logger = logging.getLogger(__name__)

def log_tool_error(tool_name: str, symbol: str, error: AgentError):
    logger.warning(
        f"Tool error: {tool_name}({symbol}) → {error.code}: {error.message}"
    )
```

用于 Phase 6 的评测分析：统计哪些错误最常发生，优化工具实现或提示词。
