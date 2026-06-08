# -*- coding: utf-8 -*-
"""
Agent 基类 - 带 LLM 推理能力

为什么需要重写？
- 旧版本：固定调用工具，无推理能力
- 新版本：调用 LLM，LLM 决定调用哪些工具

参考 daily_stock_analysis 的 base_agent.py 设计
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .protocols import AgentContext, AgentOpinion, StageResult, StageStatus
from .llm_adapter import LLMToolAdapter


class BaseAgent(ABC):
    """
    Agent 基类
    
    为什么这样设计？
    - 每个 Agent 有自己的 LLM 适配器
    - 每个 Agent 有自己的系统提示词
    - LLM 决定调用哪些工具（动态）
    - LLM 推理后输出判断
    """
    
    # 子类必须定义
    agent_name: str = "base"
    tool_names: Optional[List[str]] = None  # None = 所有工具可用
    max_steps: int = 6  # 最大步数
    
    def __init__(self, llm_adapter: LLMToolAdapter, tool_registry=None):
        """
        初始化 Agent
        
        Args:
            llm_adapter: LLM 适配器
            tool_registry: 工具注册表
        """
        self.llm_adapter = llm_adapter
        self.tool_registry = tool_registry
    
    @abstractmethod
    def system_prompt(self, ctx: AgentContext) -> str:
        """
        构建系统提示词（抽象方法，子类必须实现）
        
        为什么是抽象方法？
        - 每个 Agent 的角色不同
        - Technical Agent：技术分析专家
        - Intel Agent：消息面专家
        - Decision Agent：决策专家
        """
        pass
    
    @abstractmethod
    def build_user_message(self, ctx: AgentContext) -> str:
        """
        构建用户消息（抽象方法，子类必须实现）
        
        为什么是抽象方法？
        - 每个 Agent 需要的信息不同
        - Technical Agent：需要股票代码
        - Intel Agent：需要股票代码
        - Decision Agent：需要前两个 Agent 的观点
        """
        pass
    
    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        """
        处理 LLM 原始输出（可重写）
        
        默认：返回 None（只存储原始文本）
        子类可以重写，解析 JSON 输出
        
        Args:
            ctx: Agent 上下文
            raw_text: LLM 原始输出
        
        Returns:
            AgentOpinion 或 None
        """
        return None
    
    def run(self, ctx: AgentContext) -> StageResult:
        """
        执行 Agent（模板方法）
        
        流程：
        1. 构建系统提示词
        2. 构建用户消息
        3. 调用 LLM
        4. 如果 LLM 调用工具，执行工具
        5. 重复 3-4 直到 LLM 输出文本
        6. 处理输出，生成 AgentOpinion
        
        Args:
            ctx: Agent 上下文
        
        Returns:
            StageResult: 阶段结果
        """
        try:
            # 1. 构建提示词
            system = self.system_prompt(ctx)
            user_msg = self.build_user_message(ctx)
            
            # 2. 准备工具定义
            tools = self._get_tool_definitions()
            
            # 3. 执行 Agent Loop（ReAct 模式）
            messages = [{"role": "user", "content": user_msg}]
            all_tool_calls = []
            
            for step in range(self.max_steps):
                # 调用 LLM（每轮都传完整messages和tools）
                result = self.llm_adapter.chat(
                    system=system,
                    user_message=user_msg if step == 0 else "",
                    tools=tools,
                    messages=messages,
                )
                
                # 如果有工具调用，执行
                if result.get("tool_calls"):
                    # 执行工具
                    tool_results = self.llm_adapter.execute_tool_calls(
                        result["tool_calls"],
                        self._execute_tool
                    )
                    all_tool_calls.extend(result["tool_calls"])
                    
                    # 将工具结果添加到消息历史
                    if result["content"]:
                        messages.append({"role": "assistant", "content": result["content"]})
                    messages.append({"role": "user", "content": json.dumps(tool_results, ensure_ascii=False)})
                    
                    # 继续循环
                    continue
                else:
                    # 没有工具调用，LLM 输出了文本
                    raw_text = result.get("content", "")
                    break
            else:
                # 循环结束，使用最后一次的结果
                raw_text = result.get("content", "")
            
            # 4. 处理输出
            opinion = self.post_process(ctx, raw_text)
            
            # 5. 返回结果
            return StageResult(
                stage_name=self.agent_name,
                status=StageStatus.COMPLETED,
                opinion=opinion,
                meta={
                    "raw_text": raw_text,
                    "tool_calls": all_tool_calls,
                    "steps": step + 1
                }
            )
        
        except Exception as e:
            return StageResult(
                stage_name=self.agent_name,
                status=StageStatus.FAILED,
                error=str(e)
            )
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取工具定义（供 LLM 使用）"""
        if self.tool_registry is None:
            return []
        
        # 如果指定了 tool_names，只返回这些工具
        if self.tool_names is not None:
            return [t for t in self.tool_registry.get_definitions() 
                    if t["name"] in self.tool_names]
        
        # 否则返回所有工具
        return self.tool_registry.get_definitions()
    
    def _execute_tool(self, name: str, params: Dict[str, Any]) -> str:
        """执行工具调用"""
        if self.tool_registry is None:
            return json.dumps({"error": "No tool registry"})
        
        return self.tool_registry.execute(name, params)


# 需要导入 json
import json
