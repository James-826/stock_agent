# -*- coding: utf-8 -*-
"""
多 Agent 编排器 - 协调多个 Agent 工作

为什么需要重写？
- 旧版本：简单按顺序执行 Agent
- 新版本：管理 Agent 生命周期，传递上下文，收集结果

参考 daily_stock_analysis 的 orchestrator.py 设计
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from .protocols import AgentContext, AgentOpinion, StageResult, StageStatus
from .llm_adapter import LLMToolAdapter


@dataclass
class OrchestratorResult:
    """
    编排器结果
    
    为什么需要这个？
    - 汇总所有 Agent 的报告
    - 提供最终的综合建议
    - 方便前端展示
    """
    success: bool = False
    content: str = ""
    dashboard: Optional[Dict[str, Any]] = None
    tool_calls_log: List[Dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0
    total_tokens: int = 0
    error: Optional[str] = None


# 有效的编排器模式
VALID_MODES = ("quick", "standard", "full")


class AgentOrchestrator:
    """
    Agent 编排器
    
    为什么这样设计？
    - 管理多个 Agent 的生命周期
    - 传递共享上下文
    - 收集和汇总结果
    """
    
    def __init__(self, llm_adapter: LLMToolAdapter, tool_registry=None, mode: str = "standard"):
        """
        初始化编排器
        
        Args:
            llm_adapter: LLM 适配器（共享）
            tool_registry: 工具注册表
            mode: 分析模式 (quick, standard, full)
        """
        self.llm_adapter = llm_adapter
        self.tool_registry = tool_registry
        self.mode = mode if mode in VALID_MODES else "standard"
        self.agents: List[BaseAgent] = []
    
    def add_agent(self, agent: BaseAgent):
        """添加 Agent"""
        self.agents.append(agent)
    
    def run(self, stock_code: str, stock_name: str = "", query: str = "") -> OrchestratorResult:
        """
        运行多 Agent 流水线
        
        流程：
        1. 创建共享上下文
        2. 根据模式选择 Agent
        3. 按顺序运行每个 Agent
        4. 收集结果
        5. 返回最终结果
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            query: 用户查询
        
        Returns:
            OrchestratorResult: 编排器结果
        """
        # 1. 创建共享上下文
        ctx = AgentContext(
            query=query,
            stock_code=stock_code,
            stock_name=stock_name,
        )
        
        # 2. 根据模式选择 Agent
        if self.mode == "quick":
            agents_to_run = self.agents[:2]  # 只用前2个
        elif self.mode == "standard":
            agents_to_run = self.agents[:3]  # 用前3个
        else:
            agents_to_run = self.agents  # 用所有
        
        # 3. 按顺序运行每个 Agent
        all_tool_calls = []
        total_steps = 0
        
        for agent in agents_to_run:
            result = agent.run(ctx)
            
            # 收集工具调用日志
            if result.meta.get("tool_calls"):
                all_tool_calls.extend(result.meta["tool_calls"])
            
            # 收集步数
            total_steps += result.meta.get("steps", 0)
            
            # 如果有观点，添加到上下文
            if result.opinion:
                ctx.add_opinion(result.opinion)
            
            # 如果失败，记录错误
            if result.status == StageStatus.FAILED:
                return OrchestratorResult(
                    success=False,
                    error=f"Agent {agent.agent_name} failed: {result.error}",
                    tool_calls_log=all_tool_calls,
                    total_steps=total_steps,
                )
        
        # 4. 收集最终结果
        final_decision = ctx.get_data("final_decision")
        
        # 5. 构建dashboard（包含opinions给前端展示）
        dashboard_data = final_decision.copy() if final_decision else {}
        dashboard_data["opinions"] = [
            {
                "agent_name": op.agent_name,
                "signal": op.signal,
                "confidence": op.confidence,
                "reasoning": op.reasoning,
            }
            for op in ctx.opinions
        ]

        # 6. 返回结果
        return OrchestratorResult(
            success=True,
            content=json.dumps(dashboard_data, ensure_ascii=False, indent=2),
            dashboard=dashboard_data,
            tool_calls_log=all_tool_calls,
            total_steps=total_steps,
        )


    def run_stream(self, stock_code, stock_name="", query=""):
        """Run pipeline and yield events as each agent completes."""
        ctx = AgentContext(query=query, stock_code=stock_code, stock_name=stock_name)
        
        if self.mode == "quick":
            agents_to_run = self.agents[:2]
        elif self.mode == "standard":
            agents_to_run = self.agents[:3]
        else:
            agents_to_run = self.agents
        
        all_tool_calls = []
        total_steps = 0
        
        for agent in agents_to_run:
            # Yield progress event
            agent_labels = {"technical": "\u6280\u672f\u9762\u5206\u6790", "intel": "\u6d88\u606f\u9762\u5206\u6790", "decision": "\u7efc\u5408\u51b3\u7b56"}
            yield {"type": "text", "content": f"\u6b63\u5728\u8fd0\u884c{agent_labels.get(agent.agent_name, agent.agent_name)}..."}
            
            result = agent.run(ctx)
            
            if result.meta.get("tool_calls"):
                all_tool_calls.extend(result.meta["tool_calls"])
            total_steps += result.meta.get("steps", 0)
            
            if result.opinion:
                ctx.add_opinion(result.opinion)
                # Yield agent completion event
                yield {"type": "agent_complete", "agent_name": agent.agent_name, "signal": result.opinion.signal, "confidence": result.opinion.confidence}
            
            if result.status == StageStatus.FAILED:
                yield {"type": "text", "content": f"\u274c {agent.agent_name} \u5206\u6790\u5931\u8d25: {result.error}"}
                return
        
        # Build final dashboard
        final_decision = ctx.get_data("final_decision")
        dashboard_data = final_decision.copy() if final_decision else {}
        dashboard_data["opinions"] = [
            {"agent_name": op.agent_name, "signal": op.signal, "confidence": op.confidence, "reasoning": op.reasoning}
            for op in ctx.opinions
        ]
        
        yield {"type": "analysis_result", "result": dashboard_data}
        yield {"type": "final_response", "content": json.dumps(dashboard_data, ensure_ascii=False, indent=2)}


# 需要导入 json
import json
