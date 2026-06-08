# -*- coding: utf-8 -*-
"""
技术面分析 Agent - 带 LLM 推理能力

为什么需要重写？
- 旧版本：固定调用 analyze_trend，无推理
- 新版本：LLM 决定调用哪些工具，推理后输出判断

参考 daily_stock_analysis 的 technical_agent.py 设计
"""

import json
from typing import Optional
from .base import BaseAgent
from .protocols import AgentContext, AgentOpinion
from .llm_adapter import LLMToolAdapter


class TechnicalAgent(BaseAgent):
    """
    技术面分析 Agent
    
    职责：
    - 获取实时行情和历史 K线
    - 运行技术指标分析（MA、MACD、RSI）
    - 输出结构化的技术面判断
    """
    
    agent_name = "technical"
    max_steps = 6
    tool_names = [
        "stock_quote",
        "stock_kline",
        "analyze_trend",
    ]
    
    def __init__(self, llm_adapter: LLMToolAdapter, tool_registry=None):
        """初始化 Technical Agent"""
        super().__init__(llm_adapter, tool_registry)
    
    def system_prompt(self, ctx: AgentContext) -> str:
        """
        构建系统提示词
        
        为什么这样设计？
        - 告诉 LLM 它是技术分析专家
        - 定义工作流程
        - 定义输出格式
        """
        return """\
You are a **Technical Analysis Agent** specialising in stock analysis.

**IMPORTANT: Output ALL text in Chinese (中文). All reasoning, summaries, and analysis must be in Chinese.**

Your task: perform a thorough technical analysis of the given stock and \
output a structured JSON opinion.

## Workflow (execute stages in order)
1. Fetch realtime quote (stock_quote tool)
2. Fetch daily K-line history (stock_kline tool)
3. Run comprehensive trend analysis (analyze_trend tool)
4. Analyse the results

## Output Format
Return **only** a JSON object (no markdown fences):
{
  "signal": "strong_buy|buy|hold|sell|strong_sell",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentence summary of technical analysis",
  "key_levels": {
    "support": <float>,
    "resistance": <float>,
    "stop_loss": <float>
  },
  "trend_score": 0-100,
  "ma_alignment": "bullish|neutral|bearish",
  "rsi_status": "overbought|neutral|oversold",
  "macd_signal": "golden_cross|death_cross|neutral"
}
"""
    
    def build_user_message(self, ctx: AgentContext) -> str:
        """
        构建用户消息
        
        为什么这样设计？
        - 提供股票代码
        - 指示 LLM 使用工具
        """
        parts = [f"Perform technical analysis on stock **{ctx.stock_code}**"]
        if ctx.stock_name:
            parts[0] += f" ({ctx.stock_name})"
        parts.append("Use your tools to fetch data, then output the JSON opinion.")
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
            # 移除可能的 markdown 代码块
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()
            
            parsed = json.loads(text)
            
            return AgentOpinion(
                agent_name=self.agent_name,
                signal=parsed.get("signal", "hold"),
                confidence=float(parsed.get("confidence", 0.5)),
                reasoning=parsed.get("reasoning", ""),
                key_levels={
                    k: float(v) for k, v in parsed.get("key_levels", {}).items()
                    if isinstance(v, (int, float))
                },
                raw_data=parsed,
            )
        except (json.JSONDecodeError, ValueError):
            # JSON 解析失败，使用原始文本
            return AgentOpinion(
                agent_name=self.agent_name,
                signal="hold",
                confidence=0.3,
                reasoning=raw_text[:500],  # 截取前500字符
                raw_data={"raw_text": raw_text}
            )
