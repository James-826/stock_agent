# -*- coding: utf-8 -*-
import sys
import os
os.chdir("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent")
sys.path.insert(0, "src")

from src.agents.technical import TechnicalAgent
from src.agents.intel import IntelAgent
from src.agents.decision import DecisionAgent
from src.agents.orchestrator import AgentOrchestrator

print("=== Multi-Agent Pipeline Test ===")
print()

# Create agents
technical_agent = TechnicalAgent()
intel_agent = IntelAgent()
decision_agent = DecisionAgent()

# Create orchestrator
orchestrator = AgentOrchestrator()
orchestrator.add_agent(technical_agent)
orchestrator.add_agent(intel_agent)
orchestrator.add_agent(decision_agent)

print("Running standard pipeline for NVDA...")
print()

# Run pipeline
result = orchestrator.run_pipeline("NVDA", mode="standard")

# Display results
print(f"Symbol: {result.symbol}")
print(f"Mode: {result.mode}")
print(f"Final Signal: {result.final_signal}")
print(f"Final Score: {result.final_score}/100")
print(f"Final Confidence: {result.final_confidence:.1%}")
print()
print("=== Agent Reports ===")
for report in result.agent_reports:
    print(f"\n{report.agent_name}:")
    print(f"  Signal: {report.signal}")
    print(f"  Confidence: {report.confidence:.1%}")
    print(f"  Key Findings: {report.key_findings}")
    print(f"  Summary: {report.summary}")
print()
print("=== Final Summary ===")
print(result.summary)
