# -*- coding: utf-8 -*-
"""
共享协议 - 多 Agent 通信的数据结构

为什么需要这个文件？
- 定义 Agent 之间传递的数据格式
- AgentContext：共享上下文，所有 Agent 都能读写
- AgentOpinion：每个 Agent 的分析结论

参考 daily_stock_analysis 的 protocols.py 设计
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Signal(str, Enum):
    """标准化的交易信号"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class StageStatus(str, Enum):
    """流水线阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentContext:
    """
    共享上下文 - 单次分析运行的共享状态
    
    为什么需要这个？
    - 所有 Agent 共享同一个上下文
    - 每个 Agent 可以读写上下文
    - 编排器负责初始化和收集结果
    
    类比：就像一个共享的白板，每个人都可以在上面写东西
    """
    
    # --- 身份信息 ---
    query: str = ""  # 用户查询
    stock_code: str = ""  # 股票代码
    stock_name: str = ""  # 股票名称
    session_id: str = ""  # 会话 ID
    
    # --- 收集的数据（由数据获取阶段填充）---
    data: Dict[str, Any] = field(default_factory=dict)
    # 典型键："realtime_quote", "daily_history", "trend_result", "news"
    
    # --- 各个 Agent 的观点 ---
    opinions: List["AgentOpinion"] = field(default_factory=list)
    
    # --- 风险标记 ---
    risk_flags: List[Dict[str, Any]] = field(default_factory=list)
    
    # --- 任意元数据 ---
    meta: Dict[str, Any] = field(default_factory=dict)
    
    # --- 时间戳 ---
    created_at: float = field(default_factory=time.time)
    
    def add_opinion(self, opinion: "AgentOpinion") -> None:
        """添加一个 Agent 的观点"""
        if opinion.timestamp == 0:
            opinion.timestamp = time.time()
        self.opinions.append(opinion)
    
    def add_risk_flag(self, category: str, description: str, severity: str = "medium") -> None:
        """添加风险标记"""
        self.risk_flags.append({
            "category": category,
            "description": description,
            "severity": severity,
            "timestamp": time.time(),
        })
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any) -> None:
        """设置数据"""
        self.data[key] = value
    
    @property
    def has_risk_flags(self) -> bool:
        """是否有风险标记"""
        return len(self.risk_flags) > 0


@dataclass
class AgentOpinion:
    """
    Agent 观点 - 单个 Agent 的分析结论
    
    为什么需要这个？
    - 标准化 Agent 的输出格式
    - 方便下游 Agent 消费
    - 可以序列化和日志记录
    """
    
    agent_name: str = ""  # Agent 名称
    signal: str = ""  # 信号：strong_buy, buy, hold, sell, strong_sell
    confidence: float = 0.0  # 置信度 0-1
    reasoning: str = ""  # 推理过程
    key_levels: Dict[str, float] = field(default_factory=dict)  # 关键价位
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始数据
    timestamp: float = 0.0  # 时间戳
    
    def __post_init__(self) -> None:
        """确保置信度在 0-1 范围内"""
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


@dataclass
class StageResult:
    """
    阶段结果 - 单个 Agent 执行的结果
    
    为什么需要这个？
    - 封装 Agent 的执行结果
    - 包含状态、观点、元数据
    - 方便编排器收集和处理
    """
    
    stage_name: str = ""  # 阶段名称
    status: StageStatus = StageStatus.PENDING  # 状态
    opinion: Optional[AgentOpinion] = None  # Agent 观点
    meta: Dict[str, Any] = field(default_factory=dict)  # 元数据
    error: Optional[str] = None  # 错误信息
