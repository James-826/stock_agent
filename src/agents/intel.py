# -*- coding: utf-8 -*-
"""
消息面分析 Agent - 带 LLM 推理能力

为什么需要重写？
- 旧版本：固定调用 stock_news，无推理
- 新版本：LLM 决定调用哪些工具，推理后输出判断

参考 daily_stock_analysis 的 intel_agent.py 设计
"""

import json
from typing import Optional
from .base import BaseAgent
from .protocols import AgentContext, AgentOpinion
from .llm_adapter import LLMToolAdapter


class IntelAgent(BaseAgent):
    """
    消息面分析 Agent
    
    职责：
    - 搜索最新新闻和公告
    - 检测风险事件
    - 总结情绪和催化剂
    """
    
    agent_name = "intel"
    max_steps = 4
    tool_names = [
        "stock_news",
        "stock_quote",
    ]
    
    def __init__(self, llm_adapter: LLMToolAdapter, tool_registry=None):
        """初始化 Intel Agent"""
        super().__init__(llm_adapter, tool_registry)
    
    def system_prompt(self, ctx: AgentContext) -> str:
        """
        构建系统提示词
        
        为什么这样设计？
        - 告诉 LLM 它是消息面专家
        - 定义工作流程
        - 定义输出格式
        """
        return """\
You are an **Intelligence & Sentiment Agent** specialising in stock analysis.

Your task: gather the latest news, announcements, and risk signals for \
the given stock, then produce a structured JSON opinion.

## Workflow
1. Search latest stock news (stock_news tool)
2. Get current price for context (stock_quote tool)
3. Classify positive catalysts and risk alerts
4. Assess overall sentiment

## Risk Detection Priorities
- Insider / major shareholder sell-downs
- Earnings warnings or pre-loss announcements
- Regulatory penalties or investigations
- Industry-wide policy headwinds

## Output Format
Return **only** a JSON object:
{
  "signal": "strong_buy|buy|hold|sell|strong_sell",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentence summary of news/sentiment findings",
  "risk_alerts": ["list", "of", "detected", "risks"],
  "positive_catalysts": ["list", "of", "catalysts"],
  "sentiment_label": "very_positive|positive|neutral|negative|very_negative",
  "key_news": [
    {"title": "...", "impact": "positive|negative|neutral"}
  ]
}
"""
    
    def build_user_message(self, ctx: AgentContext) -> str:
        """
        构建用户消息
        
        为什么这样设计？
        - 提供股票代码
        - 指示 LLM 使用工具
        """
        parts = [f"Gather intelligence and assess sentiment for stock **{ctx.stock_code}**"]
        if ctx.stock_name:
            parts[0] += f" ({ctx.stock_name})"
        parts.append(
            "Steps:\n"
            "1. Call stock_news to get latest news.\n"
            "2. Call stock_quote to get current price.\n"
            "3. Output the JSON opinion."
        )
        return "\n".join(parts)
    
    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        """
        处理 LLM 输出
        
        为什么需要这个？
        - LLM 输出可能是 JSON 或纯文本
        - 需要解析为 AgentOpinion
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
            
            # 缓存解析结果，供下游 Agent 使用
            ctx.set_data("intel_opinion", parsed)
            
            # 传播风险标记
            for alert in parsed.get("risk_alerts", []):
                if isinstance(alert, str) and alert:
                    ctx.add_risk_flag(category="intel", description=alert)
            
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
