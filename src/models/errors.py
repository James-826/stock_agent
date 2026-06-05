# -*- coding: utf-8 -*-
"""错误码定义。

为什么要单独定义错误码？
  - 工具执行可能失败（股票代码不存在、网络超时、数据源无数据）
  - 模型需要知道"发生了什么错误"才能决定下一步（重试？换个代码？提示用户？）
  - 对应 Phase 2 学的 Error Handling：错误信息放入上下文，模型自己判断策略

对应 oss 项目的 ERROR_DEFINITIONS（20+ 错误码 + 恢复操作）。
我们这里简化版，只定义股票场景的错误。
"""

from pydantic import BaseModel
from typing import Optional


class AgentError(BaseModel):
    """Agent 错误类型。
    
    和 oss 的 AgentError 对应：
      code: 错误码（机器可读）
      title: 错误标题（人类可读）
      message: 详细信息
      can_retry: 是否可以重试
    """
    code: str
    title: str
    message: str
    can_retry: bool = False


# 预定义的错误码
# 工具函数返回这些，Agent Loop 把它们放入上下文，模型自己决定怎么处理
ERROR_DEFINITIONS: dict[str, AgentError] = {
    # 股票代码不存在
    "SYMBOL_NOT_FOUND": AgentError(
        code="SYMBOL_NOT_FOUND",
        title="股票代码不存在",
        message="找不到该股票代码，请检查是否正确。A股代码如 600519，美股如 AAPL",
        can_retry=False,  # 不能重试，需要用户换个代码
    ),
    # 数据源暂时不可用
    "DATA_UNAVAILABLE": AgentError(
        code="DATA_UNAVAILABLE",
        title="数据暂时不可用",
        message="数据源暂时无法访问，请稍后重试",
        can_retry=True,  # 可以重试
    ),
    # 网络超时
    "NETWORK_TIMEOUT": AgentError(
        code="NETWORK_TIMEOUT",
        title="网络超时",
        message="请求超时，请检查网络连接后重试",
        can_retry=True,
    ),
    # 参数错误（模型传了错误的参数）
    "INVALID_PARAMS": AgentError(
        code="INVALID_PARAMS",
        title="参数错误",
        message="工具调用参数不正确",
        can_retry=False,
    ),
}
