# -*- coding: utf-8 -*-
"""models 包的初始化文件。

作用：让其他模块可以这样导入：
  from ..models import QuoteResult, AgentError, ERROR_DEFINITIONS
而不是：
  from ..models.tool_result import QuoteResult
  from ..models.errors import AgentError
"""

from .tool_result import (
    QuoteResult,
    KlineResult,
    ValuationResult,
    NewsItem,
    NewsResult,
)
from .errors import AgentError, ERROR_DEFINITIONS
from .state import UserContext
