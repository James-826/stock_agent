# -*- coding: utf-8 -*-
"""Agent 状态定义。

状态是什么？
  - Agent 在多轮对话中需要记住的信息
  - 比如用户关注哪些股票、偏好什么市场、用什么语言

对应 oss 项目的 session 状态管理。
我们这里简化：只跟踪用户的基本上下文。
"""

from pydantic import BaseModel
from typing import Optional


class UserContext(BaseModel):
    """用户上下文（跨轮次保持的信息）。
    
    为什么需要这个？
      - 用户第一轮说"看茅台"，第二轮说"它的PE呢"
      - "它"指的是茅台，Agent 需要记住
      - 这个信息存在 UserContext 里，每轮拼入提示词
    """
    default_market: str = "US"           # 默认市场
    mentioned_symbols: list[str] = []    # 用户提过的股票代码
    language: str = "zh"                 # 用户语言
