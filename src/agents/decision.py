# -*- coding: utf-8 -*-
"""
决策 Agent - 带 LLM 推理能力

为什么需要重写？
- 旧版本：简单汇总前两个 Agent 的结果
- 新版本：LLM 理解前两个 Agent 的观点，推理后输出最终决策

参考 daily_stock_analysis 的 decision_agent.py 设计
"""

import json
from typing import Optional
from .base import BaseAgent
from .protocols import AgentContext, AgentOpinion
from .llm_adapter import LLMToolAdapter


class DecisionAgent(BaseAgent):
    """
    决策 Agent
    
    职责：
    - 综合 Technical Agent 和 Intel Agent 的观点
    - 做出最终买卖决策
    - 输出结构化的决策报告
    """
    
    agent_name = "decision"
    max_steps = 3  # 纯综合，不需要很多工具调用
    tool_names = []  # 不使用工具，只基于上下文
    
    def __init__(self, llm_adapter: LLMToolAdapter, tool_registry=None):
        """初始化 Decision Agent"""
        super().__init__(llm_adapter, tool_registry)
    
    def system_prompt(self, ctx: AgentContext) -> str:
        """
        构建系统提示词
        
        为什么这样设计？
        - 告诉 LLM 它是决策专家
        - 定义综合逻辑
        - 定义输出格式
        """
        return """\
You are a **Decision Synthesis Agent** that produces the final investment \
recommendation.

You will receive:
1. Structured opinions from a Technical Agent and an Intel Agent
2. Any risk flags raised

Your task: synthesise all inputs into a single, actionable recommendation.

## Core Principles
1. **Core conclusion first** - one sentence, clear direction
2. **Split advice** - different for no-position vs has-position
3. **Risk priority** - risk alerts must be prominent

## Signal Weighting Guidelines
- Technical opinion weight: ~40%
- Intel / sentiment weight: ~30%
- Risk flags weight: ~30% (negative override: any high-severity risk caps signal at "hold")

## Scoring
- 80-100: buy (all conditions met, high conviction)
- 60-79: buy (mostly positive, minor caveats)
- 40-59: hold (mixed signals, or risk present)
- 20-39: sell (negative trend + risk)
- 0-19: sell (major risk + bearish)

## Output Format
Return **only** a JSON object:
{
  "signal": "strong_buy|buy|hold|sell|strong_sell",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentence summary of decision rationale",
  "score": 0-100,
  "technical_summary": "brief technical summary",
  "intel_summary": "brief intel summary",
  "risk_summary": "brief risk summary",
  "action_advice": "specific action recommendation"
}
"""
    
    def build_user_message(self, ctx: AgentContext) -> str:
        """
        构建用户消息
        
        为什么这样设计？
        - 提供前两个 Agent 的观点
        - 提供风险标记
        - 指示 LLM 综合判断
        """
        parts = [
            f"# Synthesis Request for {ctx.stock_code}",
            f"Stock: {ctx.stock_code} ({ctx.stock_name})" if ctx.stock_name else f"Stock: {ctx.stock_code}",
            "",
        ]
        
        # 添加前两个 Agent 的观点
        if ctx.opinions:
            parts.append("## Agent Opinions")
            for op in ctx.opinions:
                parts.append(f"\n### {op.agent_name}")
                parts.append(f"Signal: {op.signal} | Confidence: {op.confidence:.2f}")
                parts.append(f"Reasoning: {op.reasoning}")
                if op.key_levels:
                    parts.append(f"Key levels: {json.dumps(op.key_levels)}")
                if op.raw_data:
                    extra_keys = {k: v for k, v in op.raw_data.items()
                                  if k not in ("signal", "confidence", "reasoning", "key_levels")}
                    if extra_keys:
                        parts.append(f"Extra data: {json.dumps(extra_keys, ensure_ascii=False, default=str)}")
                parts.append("")
        
        # 添加风险标记
        if ctx.risk_flags:
            parts.append("## Risk Flags")
            for rf in ctx.risk_flags:
                parts.append(f"- [{rf.get('severity', 'medium')}] {rf.get('category', '')}: {rf.get('description', '')}")
            parts.append("")
        
        parts.append("Synthesise the above into the final recommendation JSON.")
        return "\n".join(parts)
    
    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        """
        处理 LLM 输出
        
        为什么需要这个？
        - LLM 输出可能是 JSON 或纯文本
        - 需要解析为 AgentOpinion
        - 需要存储最终决策
        """
        # 尝试解析 JSON
        try:
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()
            
            parsed = json.loads(text)
            
            # 存储最终决策到上下文
            ctx.set_data("final_decision", parsed)
            
            return AgentOpinion(
                agent_name=self.agent_name,
                signal=parsed.get("signal", "hold"),
                confidence=float(parsed.get("confidence", 0.5)),
                reasoning=parsed.get("reasoning", ""),
                raw_data=parsed,
            )
        except (json.JSONDecodeError, ValueError):
            # JSON 解析失败，使用原始文本
            return AgentOpinion(
                agent_name=self.agent_name,
                signal="hold",
                confidence=0.3,
                reasoning=raw_text[:500],
                raw_data={"raw_text": raw_text}
            )
