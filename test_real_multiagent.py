# -*- coding: utf-8 -*-
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent/.env")

os.chdir("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent")
sys.path.insert(0, "src")

from src.agents.llm_adapter import LLMToolAdapter
from src.agents.technical import TechnicalAgent
from src.agents.intel import IntelAgent
from src.agents.decision import DecisionAgent
from src.agents.orchestrator import AgentOrchestrator
from src.tools.registry import TOOL_DEFINITIONS, execute_tool

# 创建工具注册表（简化版）
class SimpleToolRegistry:
    def get_definitions(self):
        return TOOL_DEFINITIONS
    
    def execute(self, name, params):
        return execute_tool(name, params)

# 创建 LLM 适配器（使用 .env 中的配置）
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
base_url = os.environ.get("BASE_URL", "https://api.anthropic.com")
model = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

print(f"API Key: {api_key[:10]}...")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
print()

llm_adapter = LLMToolAdapter(
    api_key=api_key,
    model=model,
    base_url=base_url
)

tool_registry = SimpleToolRegistry()

print("=== Real Multi-Agent Pipeline Test ===")
print()

# 创建 Agent
technical_agent = TechnicalAgent(llm_adapter, tool_registry)
intel_agent = IntelAgent(llm_adapter, tool_registry)
decision_agent = DecisionAgent(llm_adapter, tool_registry)

# 创建编排器
orchestrator = AgentOrchestrator(llm_adapter, tool_registry, mode="standard")
orchestrator.add_agent(technical_agent)
orchestrator.add_agent(intel_agent)
orchestrator.add_agent(decision_agent)

print("Running standard pipeline for NVDA...")
print("(This will call LLM 3 times - Technical, Intel, Decision)")
print()

# 运行流水线
result = orchestrator.run(stock_code="NVDA", stock_name="NVIDIA")

# 显示结果
if result.success:
    print("=== Pipeline Success ===")
    print(f"Total steps: {result.total_steps}")
    print(f"Tool calls: {len(result.tool_calls_log)}")
    print()
    print("=== Final Decision ===")
    print(result.content)
else:
    print(f"Pipeline failed: {result.error}")
